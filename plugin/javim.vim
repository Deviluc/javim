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
python3 from javim import Javim


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

function! javim#runAs()
python3 << EOF
javim.runAs(vim.eval('line(".")'), vim.eval('col(".")'))
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

:command! -nargs=1 -complete=dir ProjectImport call javim#projectImport(<f-args>)
:command! -nargs=0 EditRunConfiguration python3 javim.edit_run_configurations()

augroup javim
    autocmd!
    autocmd BufEnter * :call javim#bufEnter(expand("<abuf>"))
    autocmd BufDelete * :call javim#bufDelete(expand("<abuf>"))
    autocmd VimLeave * call javim#vimQuit()
    "autocmd TextChanged * :call javim#processTextChanged()
    "autocmd TextChangedI * :call javim#processTextChangedI()
    "autocmd TextChangedP * :call javim#processTextChangedP()
    "autocmd TextYankPost * :call javim#processTextYank()
augroup END

:call javim#init()
