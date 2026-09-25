function runner()
diary off;
try
    draw_stack_full();
catch ME
    fid=fopen(fullfile(pwd,'matlab_err.txt'),'w');
    fprintf(fid,'IDENTIFIER: %s\n', ME.identifier);
    fprintf(fid,'MESSAGE: %s\n', ME.message);
    for k=1:numel(ME.stack)
        fprintf(fid,'STACK: %s line %d\n', ME.stack(k).name, ME.stack(k).line);
    end
    fclose(fid);
end
end
