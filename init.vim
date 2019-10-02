set nocompatible              " be iMproved, required
filetype off                  " required

" set the runtime path to include javim
let &runtimepath.=',~/git/javim'
let &runtimepath.=',~/git/tbUiTestVimPlugin'
let &runtimepath.=',~/git/javimTestngPlugin'

" set shell for termopen and friends
set shell=/bin/sh

" Plugin section for vim-plug
call plug#begin()

" coc.nvim for lsp support
Plug 'neoclide/coc.nvim', {'branch': 'release'}


" neosnippet 
Plug 'Shougo/neosnippet.vim'
Plug 'Shougo/neosnippet-snippets'

" FZF
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all'  }
Plug 'junegunn/fzf.vim'

" gruvbox theme
Plug 'morhetz/gruvbox'
" Color schemes
Plug 'rafi/awesome-vim-colorschemes'
Plug 'altercation/vim-colors-solarized'

" vimproc needed for vebugger
Plug 'Shougo/vimproc.vim', { 'do' : 'make' }
" vebugger
Plug 'idanarye/vim-vebugger', { 'branch': 'develop' }

" for xml tag closing
Plug 'alvan/vim-closetag'
" for xml support
Plug 'othree/xml.vim'
" for parenthesis closing
Plug 'cohama/lexima.vim'

" NERDTree + git
Plug 'scrooloose/nerdtree'
Plug 'Xuyuanp/nerdtree-git-plugin'


" Airline
Plug 'vim-airline/vim-airline'

" vista vim for file symbols (outline)
Plug 'liuchengxu/vista.vim'

" syntax and indent support for apache velocity
Plug 'lepture/vim-velocity'

" vimwiki to take notes and create documentations
Plug 'vimwiki/vimwiki'

" vim-startify for fancy start screen!
Plug 'mhinz/vim-startify'

" Devicons
Plug 'ryanoasis/vim-devicons'

" language pack collection
Plug 'sheerun/vim-polyglot'

" vim plugin
Plug 'tpope/vim-fugitive'

" Surround plugin 
Plug 'tpope/vim-surround'

" getter and setter for java
Plug 'Dinduks/vim-java-get-set'

call plug#end()


" Update/Install plugins on startup
":PlugUpdate

" set leader to space
let mapleader=" "
" set double leader to :
nnoremap <leader><leader> :
" set leader w to write
nnoremap <leader>w :w<CR>
" set leader b to buffer close
nnoremap <leader>b :bd<CR>
" coc config
" if hidden is not set, TextEdit might fail.
set hidden
" Smaller updatetime for CursorHold & CursorHoldI
set updatetime=300
" don't give |ins-completion-menu| messages.
set shortmess+=c
" always show signcolumns
"set signcolumn=yes
" Use <c-space> for trigger completion.
inoremap <silent><expr> <c-space> coc#refresh()
" Remap keys for gotos
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)
" Use `[c` and `]c` for navigate diagnostics
nmap <silent> [c <Plug>(coc-diagnostic-prev)
nmap <silent> ]c <Plug>(coc-diagnostic-next)
" Highlight symbol under cursor on CursorHold
autocmd CursorHold * silent call CocActionAsync('highlight')
" Remap for rename current word
nmap <leader>r <Plug>(coc-rename)
"
"" Remap for format selected region
vmap <leader>f  <Plug>(coc-format-selected)
nmap <leader>f  <Plug>(coc-format-selected)
" Remap for do codeAction of selected region, ex: `<leader>aap` for current paragraph
vmap <leader>a  <Plug>(coc-codeaction-selected)
nmap <leader>a  <Plug>(coc-codeaction-selected)
" Remap for do codeAction of current line
nmap <leader>ac  <Plug>(coc-codeaction)
" " Fix autofix problem of current line
nmap <leader>qf  <Plug>(coc-fix-current)
" Use `:Format` for format current buffer
 command! -nargs=0 Format :call CocAction('format')
" Using CocList
" Show all diagnostics
nnoremap <silent> <space>a  :<C-u>CocList diagnostics<cr>
" Manage extensions
nnoremap <silent> <space>e  :<C-u>CocList extensions<cr>
" Show commands
nnoremap <silent> <space>c  :<C-u>CocList commands<cr>
" Find symbol of current document
"nnoremap <silent> <space>o  :<C-u>CocList outline<cr>
nnoremap <space>o :Vista!!<CR>
" " Search workspace symbols
nnoremap <silent> <space>s  :<C-u>CocList -I symbols<cr>
" " Do default action for next item.
nnoremap <silent> <space>j  :<C-u>CocNext<CR>
" " Do default action for previous item.
nnoremap <silent> <space>k  :<C-u>CocPrev<CR>
" " Resume latest coc list
nnoremap <silent> <space>p  :<C-u>CocListResume<CR>"
" Show signature help on placeholder jump
autocmd User CocJumpPlaceholder call CocActionAsync('showSignatureHelp')
" Use K to show javadoc
nnoremap <silent> K :call CocAction('doHover')<CR>
" show javadoc with <leader>jd
"autocmd CursorHold * call CocActionAsync("doHover")
" Enter/exit floating window with <leader>f e/x
nnoremap <expr><leader>fx coc#util#has_float() ? coc#util#float_scroll(1) : "\<C-x>"
nnoremap <expr><leader>fe coc#util#has_float() ? coc#util#float_scroll(0) : "\<C-e>"
" hide all floating windows with <leader>fh
nnoremap <leader>fh :call coc#util#float_hide()<CR>

" FZF config
let g:fzf_action = {
  \ 'ctrl-t': 'tab split',
  \ 'ctrl-x': 'split',
  \ 'ctrl-v': 'vsplit',
  \ 'ctrl-o': 'ped' }
" CTRL+P for files
nmap <C-p> :Files<CR>


" set theme/color scheme
"set background=dark    " Setting dark mode
"colorscheme gruvbox
" For Neovim 0.1.3 and 0.1.4
let $NVIM_TUI_ENABLE_TRUE_COLOR=1

" Or if you have Neovim >= 0.1.5
if (has("termguicolors"))
 set termguicolors
endif

" Theme
syntax enable
set background=dark
colorscheme gruvbox

" Exit terminal with esc
au TermOpen * tnoremap <Esc> <c-\><c-n>
au FileType fzf tunmap <Esc>

" configure line breaks
let &lbr = '1'
let &showbreak='~~> '
let &breakindent = '1'

" add NERDTree mapping
nnoremap <c-n> :NERDTreeToggle<CR>
nnoremap <leader>nf :NERDTreeFind<CR>

" line numbering
:set number relativenumber

:augroup numbertoggle
:  autocmd!
:  autocmd BufEnter,FocusGained,InsertLeave * set number relativenumber
:  autocmd BufLeave,FocusLost,InsertEnter   * set number norelativenumber
:augroup END

" Airline config
let g:airline#extensions#tabline#enabled = 1

" Neosnippet config
let g:neosnippet#snippets_directory='~/.vim/bundle/vim-snippets/snippets'"
let g:coc_snippet_next='<c-k>'
let g:coc_snippet_prev='<c-j>'


" Remmap backspace to :nohl in normal mode
nnoremap <bs> :nohl<CR>

" move tabs with CTRL + HL in normal mode
nnoremap <c-h> :bp<CR>
nnoremap <c-l> :bn<CR>

" filenames for xml close-tags
let g:closetag_filenames = '*.html,*.xhtml,*.phtml,*.xml,*.vm'

" format xml
"com! FormatXML :%!python3 -c "import xml.dom.minidom, sys; print(xml.dom.minidom.parse(sys.stdin).toprettyxml())"
com! FormatXML :%!XMLLINT_INDENT=`echo -e '\t'` xmllint --format -
nnoremap <leader>xf :FormatXML<CR>

" set leader key for debugging
let g:vebugger_leader = '<CR>'

" prevent splits from resizing automaticly
set noequalalways

" set utf-8
set encoding=UTF-8

" highlight current line
set cursorline

" allow folding via indentation for xml
augroup XML
    autocmd!
    autocmd FileType xml setlocal foldmethod=indent foldlevelstart=999 foldminlines=0
augroup END

" auto refresh unmodified files that changed on disk
set autoread

" set Jenkinsfile format to groovy
au BufNewFile,BufRead Jenkinsfile setf groovy
