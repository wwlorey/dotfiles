call plug#begin('~/.config/nvim/plugged')
Plug 'ap/vim-css-color'
Plug 'christoomey/vim-tmux-navigator'
Plug 'dyng/ctrlsf.vim'
Plug 'github/copilot.vim'
Plug 'junegunn/fzf'
Plug 'maxmellon/vim-jsx-pretty'
Plug 'preservim/nerdtree'
Plug 'projekt0n/github-nvim-theme'
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-rhubarb'
Plug 'tpope/vim-sleuth'
Plug 'tpope/vim-surround'
Plug 'vim-python/python-syntax'
Plug 'yuezk/vim-js'
call plug#end()


" GENERAL CONFIGURATION

let mapleader = " "
inoremap jk <Esc>
set encoding=utf-8

" Use jk to traverse virtual lines (lines that wrap)
noremap <silent> <expr> j (v:count == 0 ? 'gj' : 'j')
noremap <silent> <expr> k (v:count == 0 ? 'gk' : 'k')

" Paste from clipboard
cnoremap <C-v> <C-r>*
inoremap <C-v> <C-r>*

" Yank to system clipboard
set clipboard+=unnamedplus

" Better Y behavior
nmap Y y$

" <C-b> is hard to reach and default <C-u> doesn't invert <C-f>
nmap <C-u> <C-b>
vmap <C-u> <C-b>

" Syntax highlighting
syntax on

" Enable mouse in all modes
set mouse=a

" Line numbers
set number

" Default tab/shift width
" TODO: Auto-detect tab width
set tabstop=2
set shiftwidth=2

" Insert the appropriate number of spaces when <Tab> is pressed
set expandtab

" Spellchecking
set spell

" https://stackoverflow.com/questions/2287440/how-to-do-case-insensitive-search-in-vim
set ignorecase
set smartcase

" Don't show the mode because it's already in the status line.
set noshowmode

" Copy file name
nmap <leader>cn :let @+=expand("%:t")<CR>
" Copy relative file path
nmap <leader>cr :let @+=expand("%")<CR>
" Copy file path
nmap <leader>cp :let @+=expand("%:p")<CR>

" Integrated terminal
" Open the terminal in a new horizontal split and enter insert mode
map <leader>` :split<CR>:terminal<CR>i
" Open the terminal in a new tab and enter insert mode
map <leader>~ :tabnew<CR>:terminal<CR>i
" Use escape to close the terminal
tnoremap <Esc> <C-\><C-n>

" Natural split behavior
set splitbelow
set splitright

" Open previously opened buffer in new split
nmap <leader>v :vsplit<CR><C-^>
nmap <leader>h :split<CR><C-^>

" Find & replace in entire file
nmap <leader>r :%s/
" Find & replace in visual selection
vmap <leader>r :s/\%V

" https://vi.stackexchange.com/questions/1983/how-can-i-get-vim-to-stop-putting-comments-in-front-of-new-lines
au FileType * set fo-=c fo-=r fo-=o

" Copy configuration to home directory and source the vim config
nmap <leader>so :!save-config<CR>:so $VIMRC<CR>

" Save this session
" Use -S to open a session
nmap <leader>ms :mksession! ~/Scratch/session.vim<CR>
nmap <leader>mn :mksession 

" Open help in a new tab
cnoreabbrev th tab help

" Hide intro message on startup
set shortmess+=I


" NERDTREE

nmap <C-e> :NERDTreeToggle<CR>
nmap <leader>er :NERDTreeFind<CR>

" Set a bookmark for the current buffer. Must be called from within a buffer.
nmap <leader>bs :NERDTreeFind<CR>:Bookmark<CR>
nmap <leader>bc :NERDTree<CR>:ClearAllBookmarks<CR>

let NERDTreeShowHidden = 1
let NERDTreeStatusline = -1
let NERDTreeMapActivateNode = "<Tab>"
let NERDTreeMapOpenInTab = "<C-t>"
let NERDTreeMapOpenVSplit = "<C-v>"
let NERDTreeMapOpenSplit = "<C-h>"

" Hide help prompt
let NERDTreeMinimalUI = 1

" Change current working directory when NERDTree root dir is changed
let g:NERDTreeChDirMode = 2

" Workaround for https://github.com/preservim/nerdtree/issues/1321
let g:NERDTreeMinimalMenu=1


" FZF

map <C-p> :FZF<CR>
let g:fzf_action = {
    \ 'ctrl-t': 'tab split',
    \ 'ctrl-h': 'split',
    \ 'ctrl-v': 'vsplit' 
    \}


" CTRLSF

map <C-s> :CtrlSFToggle<CR>
map <leader>sf :CtrlSF -hidden 
map <leader>sc <Plug>CtrlSFCwordExec
map <leader>sv <Plug>CtrlSFVwordExec
let g:ctrlsf_confirm_save = 0
let g:ctrlsf_ignore_dir = ['.git', 'node_modules']
let g:ctrlsf_auto_focus = {
    \ "at" : "done",
    \ "duration_less_than": 1000
\ }
let g:ctrlsf_mapping = {
    \ "open"    : ["<CR>", "o"],
    \ "openb"   : "O",
    \ "split"   : "<C-H>",
    \ "vsplit"  : "<C-V>",
    \ "tab"     : "<C-T>",
    \ "tabb"    : "T",
    \ "popen"   : "p",
    \ "popenf"  : "P",
    \ "quit"    : "q",
    \ "next"    : "<Tab>",
    \ "prev"    : "<S-Tab>",
    \ "nfile"   : "}",
    \ "pfile"   : "{",
    \ "pquit"   : "q",
    \ "loclist" : "",
    \ "chgmode" : "M",
    \ "stop"    : "<C-C>",
    \ "fzf"     : "<C-P>",
\ }


" GITHUB COPILOT

nmap <leader>co :Copilot panel<CR>

" Avoid the ALT key for Copilot mappings because it doesn't play nice with Mac
inoremap <C-[> <Plug>(copilot-previous)
inoremap <C-]> <Plug>(copilot-next)
inoremap <C-\> <Plug>(copilot-dismiss)


" FUGITIVE

" Open full screen fugitive summary
nmap <C-g> :0G<CR>

" Git aliases from .bashrc
cnoreabbrev ga G add
cnoreabbrev gaa G add --all
cnoreabbrev gb G branch
cnoreabbrev gbc G branch --show-current
cnoreabbrev gc G checkout
cnoreabbrev gcb G checkout -b
cnoreabbrev gcm G commit -m
cnoreabbrev gd G diff
cnoreabbrev gdi G diff --ignore-space-change
cnoreabbrev gds G diff --staged
cnoreabbrev gdss G diff --staged --stat
cnoreabbrev gl G log --graph
cnoreabbrev glp G log --patch
cnoreabbrev gpul G pull
cnoreabbrev gpus G push
cnoreabbrev gpusi !git-push-init
cnoreabbrev gs G status
cnoreabbrev gsh G stash
cnoreabbrev gshl G stash list
cnoreabbrev gshp G stash pop
cnoreabbrev gsmui G submodule update --init


" COMMENTARY

autocmd FileType javascriptreact setlocal commentstring=/*\ %s\ */


" TABS

" Always show tabline
set showtabline=2

" Quit the current tab
cnoreabbrev qt windo bd

nmap <leader>gt :tabmove +<CR>
nmap <leader>gT :tabmove -<CR>
nmap <C-t> :tabnew<CR>

function GetTabLine()
  let tabLine = ''
  let thisTabNumber = tabpagenr()
  let thisBufferName = expand('%:t')

  " Write buffer names
  for bufferNumber in tabpagebuflist(thisTabNumber)
    let bufferName = fnamemodify(bufname(bufferNumber), ':t')

    " Highlight the current buffer
    if bufferName != '' && bufferName == thisBufferName
      let tabLine ..= '%#TabLineSel#'
    else
      let tabLine ..= '%#TabLine#'
    endif

    let tabLine ..= ' '..bufferName..' '
  endfor

  let tabLine ..= '%#TabLineFill#'         " Reset tab fill
  let tabLine ..= '%='                     " Horizontal fill

  " Write tab numbers
  for tabNumber in range(1, tabpagenr('$'))
    " Highlight the current tab
    if tabNumber == thisTabNumber
      let tabLine ..= '%#TabLineSel#'
    else
      let tabLine ..= '%#TabLine#'
    endif
    
    let tabLine ..= '%'..tabNumber..'T'    " Set the tab page number to handle mouse clicks
    let tabLine ..= ' '..tabNumber..' '
  endfor

  let tabLine ..= '%#TabLineFill#'         " Reset tab fill
  let tabLine ..= '%T'                     " Reset clickable tab page number

  return tabLine
endfunction

set tabline=%!GetTabLine()


" STATUSLINE

function GetStatusLine()
  let statusLine = ''
  let statusLine ..= ' %f'        " Relative path to file in current buffer
  let statusLine ..= ' %m'        " Modified flag
  let statusLine ..= '%1*'        " Begin User1 highlight group
  let statusLine ..= '%='         " Horizontal fill
  let statusLine ..= '%*'         " End User1 highlight group
  let statusLine ..= ' %l/%L:%c'  " <current line>/<total lines>:<current column>
  let statusLine ..= '  %Y '      " File type in current buffer
  return statusLine
endfunction

set statusline=%!GetStatusLine()


" THEME

" colorscheme github_light
colorscheme github_dark
" https://vi.stackexchange.com/questions/7112/tmux-messing-with-vim-highlighting
set t_Co=256


" SYNTAX HIGHLIGHTING

let g:python_highlight_all = 1


" LINTING

augroup StellarLinting
  " Clear this group's autocmds to prevent them from piling up
  " each time this file is sourced.
  autocmd!

  autocmd BufWritePost **/stellar/**/*.js,*.jsx silent !prettier --write "%"
  autocmd BufWritePost **/stellar/**/*.py       silent !autoflake --in-place --remove-all-unused-imports "%"
  " Default configuration: ~/.config/pycodestyle
  autocmd BufWritePost **/stellar/**/*.py       silent !autopep8 --in-place "%"

augroup END

