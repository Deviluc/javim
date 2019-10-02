if !has('python')
    echo "Error: Required vim compiled with +python"
    finish
endif

" --------------------------------
" Add javim to the path
" --------------------------------
python3 import sys
python3 import vim
python3 sys.path.append(vim.eval('expand("<sfile>:h")'))
python3 import os
python3 from javim import Javim
python3 from javim.jobs import JobHandler


function! javim#init()
python3 << EOF
if 'javim' not in globals():
    print("Staring javim initialization...")
    javim = Javim(vim)
    print("Javim fully initialized!")
EOF
endfunction


function! javim#projectImport(path)
python3 << EOF

javim.project_import(vim.eval("a:path"))

EOF
endfunction

function! javim#bufEnter(buffer)
python3 << EOF
javim.buf_enter(int(vim.eval("a:buffer")))
EOF
endfunction

function! javim#bufDelete(buffer)
python3 << EOF
javim.buf_delete(int(vim.eval("a:buffer")))
EOF
endfunction

function! javim#bufSave(buffer)
python3 << EOF
javim.buf_save(int(vim.eval("a:buffer")))
EOF
endfunction

function! javim#runAs()
python3 << EOF
javim.runAs(vim.eval('line(".")'), vim.eval('col(".")'))
EOF
endfunction

function! javim#debugAs()
python3 << EOF
javim.runAs(vim.eval('line(".")'), vim.eval('col(".")'), True)
EOF
endfunction

function! javim#vimQuit()
python3 << EOF
javim.vim_quit()
EOF
endfunction

function! javim#processTextChanged()
python3 << EOF
start_row, start_col = vim.eval('getpos("\'[")[1:2]')
end_row, end_col = vim.eval('getpos("\']")[1:2]')
#if start_row != end_row or start_col != end_col:
print("Changed:", start_row, start_col, end_row, end_col)
EOF
endfunction

function! javim#processTextChangedI()
let text = @.
python3 << EOF
start_row, start_col = vim.eval('getpos("\'[")[1:2]')
end_row, end_col = vim.eval('getpos("\']")[1:2]')
#if start_row != end_row or start_col != end_col:

text = vim.eval('text')
print("ChangedI:", start_row, start_col, end_row, end_col, "Text:", text)
EOF
endfunction

function! javim#processTextChangedP()
python3 << EOF
start_row, start_col = vim.eval('getpos("'[")[1:2]')
end_row, end_col = vim.eval('getpos("']")[1:2]')
#if start_row != end_row or start_col != end_col:
text = vim.eval('@".')
print("ChangedP:", start_row, start_col, end_row, end_col, "Text:", text)
EOF
endfunction


function! javim#processTextYank()
python3 << EOF
event = vim.eval("v:event")
if event['operator'] in ["d", "D"]:
    lines = event['regcontents']
    deleted = vim.eval('@"')
    start_row, start_col = vim.eval('getpos("\'[")[1:2]')
    offset = vim.eval("line2byte(line(\"'[\"))") + start_col
    print(start_row, start_col, event, "Deleted: ", deleted)
EOF
endfunction

function! javim#handleTermClose(job_id, data, event)
python3 << EOF
job_id = int(vim.eval("a:job_id"))
data = vim.eval("a:data")
for handler in JobHandler.INSTANCES:
	handler.handle_termclose(int(job_id), data)
EOF
endfunction

function! javim#setProfiles(profiles)
python3 << EOF
javim.set_profiles(vim.eval("a:profiles"))
EOF
endfunction

:command! -nargs=1 -complete=dir ProjectImport call javim#projectImport(<f-args>)
:command! -nargs=0 EditRunConfiguration python3 javim.edit_run_configurations()
:command! -nargs=1 SetProfiles call javim#setProfiles(<f-args>)
:command! -nargs=0 ProjectOpen python3 javim.project_open()
:command! -nargs=0 ProjectClose python3 javim.project_close()
:command! -nargs=0 ProjectConfig python3 javim.edit_project_configuration()

augroup javim
    autocmd!
    autocmd BufEnter * :call javim#bufEnter(expand("<abuf>"))
    autocmd BufDelete * :call javim#bufDelete(expand("<abuf>"))
    autocmd BufWritePost * :call javim#bufSave(expand("<abuf>"))
    autocmd VimLeave * call javim#vimQuit()
    "autocmd TextChanged * :call javim#processTextChanged()
    "autocmd TextChangedI * :call javim#processTextChangedI()
    "autocmd TextChangedP * :call javim#processTextChangedP()
    "autocmd TextYankPost * :call javim#processTextYank()
augroup END

:call javim#init()


" Mappings
nnoremap <leader>ra :call javim#runAs()<CR>
nnoremap <leader>da :call javim#debugAs()<CR>
nnoremap <leader>rl python3 javim.run_last()<CR>
nnoremap <leader>dl python3 javim.run_last(True)<CR>
