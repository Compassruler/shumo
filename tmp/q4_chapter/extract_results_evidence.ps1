$ErrorActionPreference='Stop'
$base='D:\shumo\26比赛\解题\问题4_求解结果'
$dest='D:\shumo\tmp\q4_chapter\results_evidence.md'
$builder=[System.Text.StringBuilder]::new()
[void]$builder.AppendLine('# 第七章结果细审证据')
[void]$builder.AppendLine('仅提取归档 CSV 与核对绘图代码，没有重算模型，没有修改源结果。以下数值为工作精度，论文正文请适当舍入。')
$script=Get-Content -LiteralPath 'D:\shumo\tmp\q4_chapter\extract_results_evidence.py' -Encoding UTF8 -Raw
foreach($m in [regex]::Matches($script,"(?m)^say\('((?:[^'\\]|\\.)*)'\)$")){
    [void]$builder.AppendLine(($m.Groups[1].Value -replace '\\n',"`n"))
    [void]$builder.AppendLine()
}
function Load-Data([string]$name){
    $rows=@(Import-Csv -LiteralPath (Join-Path (Join-Path $base 'data') $name))
    for($i=0;$i -lt $rows.Count;$i++){ $rows[$i] | Add-Member -NotePropertyName '_line' -NotePropertyValue ($i+2) }
    return $rows
}
function Add-Table($rows,$cols,[string]$title,[string]$source=''){
    [void]$builder.AppendLine("`n### $title`n")
    [void]$builder.AppendLine("数据源：$source。_line 为含表头的 CSV 物理行号。`n")
    [void]$builder.AppendLine('| '+($cols -join ' | ')+' |')
    [void]$builder.AppendLine('| '+(($cols | ForEach-Object {'---'}) -join ' | ')+' |')
    foreach($r in $rows){
        $values=foreach($c in $cols){
            $v=[string]$r.$c; $n=0.0
            if([double]::TryParse($v,[ref]$n)){
                if([math]::Abs($n) -gt 0 -and [math]::Abs($n) -lt 0.0001){$n.ToString('G6',[cultureinfo]::InvariantCulture)}
                else{$n.ToString('0.######',[cultureinfo]::InvariantCulture)}
            }else{$v -replace "`r?`n",'；'}
        }
        [void]$builder.AppendLine('| '+($values -join ' | ')+' |')
    }
}
[void]$builder.AppendLine("`n## 9. 可直接引用的数值证据表（依上述主题顺序）`n")
$manifest=Import-Csv -LiteralPath (Join-Path $base 'figures\figure_manifest.csv')
foreach($r in $manifest){
    $paths=@($r.source_csv.Split(';') | ForEach-Object {Join-Path (Join-Path $base 'data') $_})
    $paths+=@('png','svg','pdf' | ForEach-Object {Join-Path (Join-Path $base 'figures') $r.$_})
    $exists=($paths | Where-Object { !(Test-Path -LiteralPath $_)}).Count -eq 0
    $r | Add-Member -NotePropertyName 'files_exist' -NotePropertyValue $exists
}
Add-Table $manifest @('figure','source_csv','files_exist','plot_note') '16图源CSV与输出文件核对' 'figures/figure_manifest.csv; code/plot_results.py'
$per=@(Load-Data 'per_cell_heater_energy.csv' | Where-Object strategy -eq guarded)
Add-Table $per @('_line','case','cell','energy_J','average_power_W_cm2','peak_power_W_cm2','heating_duration_s') '逐片加热指标' 'data/per_cell_heater_energy.csv'
$guards=@(Load-Data 'guarded_results.csv')
$shares=foreach($g in $guards){
    $end=($per | Where-Object {$_.case -eq $g.case -and $_.cell -in @('1','5')} | Measure-Object -Property energy_J -Sum).Sum
    [pscustomobject]@{case=$g.case;endpoint_energy_J=$end;endpoint_share_pct=100*$end/[double]$g.E_aux_J}
}
Add-Table $shares @('case','endpoint_energy_J','endpoint_share_pct') '端部两片加热占比（CSV算术汇总）' 'data/per_cell_heater_energy.csv'
$states=@(Load-Data 'controller_state_duration.csv' | Where-Object {$_.strategy -eq 'guarded' -and [double]$_.duration_s -gt 0})
Add-Table $states @('_line','case','cell','state','duration_s') '非零状态持续时长，状态1/5均为0' 'data/controller_state_duration.csv'
$obs=@(Load-Data 'observer_example_results.csv')
$obscols=@('_line','case','first_success_s','stop_s','physical_hold_s','observer_max_temperature_error_K','observer_max_ice_error','min_voltage_V','max_ice_bulk')
foreach($r in $obs){
    $cellerr=0.0; $eperr=0.0; $iceerr=0.0
    $hist=Load-Data ('trajectory_'+$r.case+'_observer_example.csv')
    foreach($row in $hist){
        if([double]$row.time_s -gt [double]$r.stop_s+1e-8){break}
        foreach($k in 1..5){
            $cellerr=[math]::Max($cellerr,[math]::Abs([double]$row."observer_T${k}_C"-[double]$row."T${k}_C"))
            $iceerr=[math]::Max($iceerr,[math]::Abs([double]$row."cell${k}_ice_est"-[double]$row."cell${k}_ice_bulk"))
        }
        foreach($side in @('EL','ER')){$eperr=[math]::Max($eperr,[math]::Abs([double]$row."observer_T${side}_C"-[double]$row."T${side}_C"))}
    }
    $r | Add-Member -NotePropertyName 'fig16_cell_temperature_error_K' -NotePropertyValue $cellerr
    $r | Add-Member -NotePropertyName 'fig16_EP_temperature_error_K' -NotePropertyValue $eperr
    $r | Add-Member -NotePropertyName 'fig16_corrected_ice_error' -NotePropertyValue $iceerr
}
Add-Table $obs ($obscols+@('fig16_cell_temperature_error_K','fig16_EP_temperature_error_K','fig16_corrected_ice_error')) '图16失配例子的原汇总及实际绘图误差峰' 'data/observer_example_results.csv; trajectory_case*_observer_example.csv'
$energy=$guards+@(Load-Data 'main_results.csv' | Where-Object strategy -eq constant_hold)
Add-Table $energy @('case','strategy','E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','charge_at_success_C_cm2','charge_at_stop_C_cm2','energy_residual_J','max_water_residual_kg') '启动能量分解' 'data/guarded_results.csv; data/main_results.csv'
Add-Table $energy @('case','strategy','final_min_T_C','final_max_T_C','final_left_EP_C','post_min_T_C','post_min_voltage_V','post_max_ice_bulk','post_energy_J') '停机状态与60s后验极值' 'data/guarded_results.csv; data/main_results.csv'
$sens=@(Load-Data 'sensitivity.csv')
Add-Table @($sens | Where-Object feasible -eq False) @('_line','case','parameter','factor','E_aux_J','first_success_s','stop_s','min_voltage_V','max_ice_bulk','physical_hold_s') '名义单因素全部失败行' 'data/sensitivity.csv'
Add-Table @($sens | Where-Object parameter -in @('G','G_EP','h')) @('_line','case','parameter','factor','E_aux_J','first_success_s','stop_s','dTmax_K','feasible') '名义物理单因素全部响应' 'data/sensitivity.csv'
Add-Table @(Load-Data 'precooling_sensitivity.csv' | Where-Object {[double]$_.cooling_min -eq 20 -and ([double]$_.conductance_factor -eq 1 -or [double]$_.h_W_m2K -eq 40)}) @('_line','h_W_m2K','conductance_factor','mean_capacity_C','field_range_K','relative_field_range','Bi_stack') '预冷20min代表参数响应' 'data/precooling_sensitivity.csv'
$stats=@()
foreach($file in @('robustness.csv','guarded_robustness.csv','constant_robustness.csv')){
    $all=@(Load-Data $file)
    foreach($g in ($all | Group-Object -Property case,strategy)){
        $rs=@($g.Group); $good=@($rs | Where-Object feasible -eq True)
        $stats+=[pscustomobject]@{file=$file;group=$g.Name;passed="$($good.Count)/$($rs.Count)";min_V=($rs | Measure-Object min_voltage_V -Minimum).Minimum;max_ice=($rs | Measure-Object max_ice_bulk -Maximum).Maximum;missing_first=@($rs | Where-Object {[double]$_.first_success_s -lt 0}).Count;missing_stop=@($rs | Where-Object {[double]$_.stop_s -lt 0}).Count;incomplete_hold=@($rs | Where-Object {[double]$_.physical_hold_completed -lt .5}).Count;seeds=(($rs.seed | Sort-Object -Unique)-join ',')}
    }
}
Add-Table $stats @('file','group','passed','min_V','max_ice','missing_first','missing_stop','incomplete_hold','seeds') '噪声与初场组事件失败统计' 'robustness/guarded_robustness/constant_robustness.csv'
Add-Table @(Load-Data 'constant_parameter_validation.csv' | Where-Object feasible -eq False) @('_line','case','strategy','seed','initial_shift_K','G_factor','G_EP_factor','h_factor','first_success_s','stop_s','physical_hold_s','min_voltage_V','max_ice_bulk') '同种子物性失配组恒功率全部失败行' 'data/constant_parameter_validation.csv'
$pilot=@(Load-Data 'guarded_pilot_robustness.csv')+@(Load-Data 'guarded_pilot_parameter_validation.csv')
Add-Table @($pilot | Where-Object feasible -eq False) @('case','seed','initial_shift_K','G_factor','G_EP_factor','h_factor','first_success_s','stop_s','min_voltage_V','max_ice_bulk') '开发期pilot失败记录' 'data/guarded_pilot_robustness.csv; data/guarded_pilot_parameter_validation.csv'
Add-Table @(Load-Data 'precooling_validation.csv') @('test','observed','tolerance','unit','passed','note') '预冷11项检验' 'data/precooling_validation.csv'
Add-Table @(Load-Data 'precooling_convergence.csv' | Where-Object {[double]$_.cooling_min -eq 20}) @('study','scale','control_volumes','dt_s','max_field_error_K','max_node_error_K','reference') '预冷20min收敛代表' 'data/precooling_convergence.csv'
$joint=@(Load-Data 'coupled_convergence.csv')
Add-Table $joint @('case','dt_s','scale','period_s','E_aux_J','first_success_s','stop_s','max_ice_bulk','min_voltage_V','feasible') '推荐策略联合加密' 'data/coupled_convergence.csv'
$deltas=foreach($case in @('case1','case2','case3')){
    $rs=@($joint | Where-Object case -eq $case | Sort-Object {[double]$_.scale})
    $a=$rs[0];$b=$rs[-1]
    [pscustomobject]@{case=$case;energy_change_pct=100*([double]$b.E_aux_J/[double]$a.E_aux_J-1);ice_change_pct=100*([double]$b.max_ice_bulk/[double]$a.max_ice_bulk-1);first_time_diff_s=[double]$b.first_success_s-[double]$a.first_success_s}
}
Add-Table $deltas @('case','energy_change_pct','ice_change_pct','first_time_diff_s') '58格0.025s至232格0.00625s直接算术比较' 'data/coupled_convergence.csv'
Add-Table @(Load-Data 'guarded_convergence.csv' | Where-Object {[double]$_.scale -eq 2 -and [double]$_.dt_s -eq .025}) @('case','period_s','E_aux_J','first_success_s','stop_s','max_ice_bulk','feasible') '推荐策略采样周期变化' 'data/guarded_convergence.csv'
[System.IO.File]::WriteAllText($dest,$builder.ToString(),[System.Text.UTF8Encoding]::new($false))
Get-Item -LiteralPath $dest | Select-Object FullName,Length
