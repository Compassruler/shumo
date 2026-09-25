function tbl = q1_read_table(cfg, fileName)
%Q1_READ_TABLE 读取 Python 导出的 UTF-8 CSV，并保留原始列名。
    path = fullfile(cfg.dataDir, fileName);
    assert(isfile(path), '找不到数据文件：%s', path);
    opts = detectImportOptions(path, 'Encoding', 'UTF-8', ...
        'VariableNamingRule', 'preserve');
    tbl = readtable(path, opts);
    assert(height(tbl) > 0, '数据文件为空：%s', path);
end
