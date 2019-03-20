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

:command! -nargs=1 -complete=dir ProjectImport call javim#projectImport(<f-args>)

augroup javim
    autocmd!
    autocmd BufEnter * :call javim#bufEnter(expand("<abuf>"))
    autocmd BufDelete * :call javim#bufDelete(expand("<abuf>"))
    autocmd VimLeave * call javim#vimQuit()
augroup END

:call javim#init()
