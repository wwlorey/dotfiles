call plug#begin('~/.config/nvim/plugged')
Plug 'ap/vim-css-color'
Plug 'bullets-vim/bullets.vim'
Plug 'christoomey/vim-tmux-navigator'
Plug 'dyng/ctrlsf.vim'
Plug 'francoiscabrol/ranger.vim'
Plug 'github/copilot.vim'
Plug 'iggredible/totitle-vim'
Plug 'junegunn/fzf'
Plug 'maxmellon/vim-jsx-pretty'
Plug 'preservim/nerdtree'
Plug 'preservim/vimux'
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-rhubarb'
Plug 'tpope/vim-sleuth'
Plug 'tpope/vim-surround'
Plug 'vim-python/python-syntax'
Plug 'wwlorey/github-nvim-theme'
Plug 'yuezk/vim-js'
call plug#end()


" GENERAL CONFIGURATION

let mapleader = " "
inoremap jk <Esc>
set encoding=utf-8

" If multiple files are provided as arguments, open the buffered files in tabs.
if argc() > 1
  tab all
endif

" Fix the escape key's behavior in insert mode
inoremap <Esc> <C-c>

" Natural traversal of virtual lines (lines that wrap)
noremap <silent> <expr> j (v:count == 0 ? 'gj' : 'j')
noremap <silent> <expr> k (v:count == 0 ? 'gk' : 'k')
noremap <silent> <expr> 0 (v:count == 0 ? 'g0' : '0')
noremap <silent> <expr> $ (v:count == 0 ? 'g$' : '$')

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
nmap <Leader>cn :let @+=expand("%:t")<CR>
" Copy relative file path
nmap <Leader>cr :let @+=expand("%")<CR>
" Copy file path
nmap <Leader>cp :let @+=expand("%:p")<CR>

" Integrated terminal
" Open the terminal in a new horizontal split and enter insert mode
map <Leader>` :split<CR>:terminal<CR>i
" Open the terminal in a new tab and enter insert mode
map <Leader>~ :tabnew<CR>:terminal<CR>i
" Use escape to close the terminal
tnoremap <Esc> <C-\><C-n>

" Natural split behavior
set splitbelow
set splitright

" Open previously opened buffer in new split
nmap <Leader>v :vsplit<CR><C-^>
nmap <Leader>h :split<CR><C-^>

" Find & replace in entire file
nmap <Leader>sr :%s/
" Find & replace in visual selection
vmap <Leader>sr :s/\%V
" Find '/' and replace with '.' in entire file
nmap <Leader>ss :%s/\//\./g<CR>
" Find '/' and replace with '.' in visual selection
vmap <Leader>ss :s/\%V\//\./g<CR>
" Remove non-numbers from the visual selection
vmap <Leader>sn :s/\%V[^0-9.]//g<CR>

" https://vi.stackexchange.com/questions/1983/how-can-i-get-vim-to-stop-putting-comments-in-front-of-new-lines
au FileType * set fo-=c fo-=r fo-=o

" Copy configuration to home directory and source the vim config
nmap <Leader>so :!save-config<CR>:so $VIMRC<CR>

" Save this session
" Use -S to open a session
nmap <Leader>ms :mksession! ~/Scratch/session.vim<CR>
nmap <Leader>mn :mksession

" Open help in a new tab
cnoreabbrev th tab help

" Hide intro message on startup
set shortmess+=I

" Prevent auto-indentation in LaTeX files.
" This was particularly a problem when it came to auto-indenting after a bracket completion.
" https://vi.stackexchange.com/a/20561
let g:tex_noindent_env=''

" Close the tmux runner (if it's open) when quitting all.
cnoreabbrev qa VimuxCloseRunner<CR>:qa<CR>


" AUTO-INSERTIONS

" Guides (i.e. "<++>") are inserted as is useful.

" HTML, Markdown
" Asterism
autocmd FileType html,markdown inoremap ;* <p style="text-align: center;">⁂</p><CR><CR>

" Markdown
autocmd FileType markdown inoremap ;a [](<++>)<Esc>?]<CR>i

" LaTeX
" Section headers
autocmd FileType tex inoremap ;1 \section{}<CR><++><Esc>?}<CR>i
autocmd FileType tex inoremap ;2 \subsection{}<CR><++><Esc>?}<CR>i
autocmd FileType tex inoremap ;3 \subsubsection{.}<CR><++><Esc>?\.}<CR>i
" Citations
autocmd FileType tex inoremap ;pc \parencite{}<++><Esc>?}<CR>i
autocmd FileType tex inoremap ;Pc \parencite[]{<++>}<++><Esc>?]<CR>i
autocmd FileType tex inoremap ;PC \parencite[cf.][]{<++>}<++><Esc>?]<CR>i
autocmd FileType tex inoremap ;tc \textcite{}<++><Esc>?}<CR>i
autocmd FileType tex inoremap ;Tc \textcite[]{<++>}<++><Esc>?]<CR>i
autocmd FileType tex inoremap ;TC \textcite[cf.][]{<++>}<++><Esc>?]<CR>i
" General
autocmd FileType tex inoremap ;i \textit{}<++><Esc>?}<CR>i
autocmd FileType tex inoremap ;b \textbf{}<++><Esc>?}<CR>i
autocmd FileType tex inoremap ;f \footnote{}<++><Esc>?}<CR>i
autocmd FileType tex inoremap ;ul \begin{itemize}<CR>\item <CR>\end{itemize}<CR><CR><++><Esc>?item<Space><CR>A
autocmd FileType tex inoremap ;ol \begin{enumerate}<CR>\item <CR>\end{enumerate}<CR><CR><++><Esc>?item<Space><CR>A
autocmd FileType tex inoremap ;li \item<Space>
autocmd FileType tex inoremap ;q “”<++><Esc>?”<CR>i
autocmd FileType tex inoremap ;su \textsuperscript{}<++><Esc>?}<CR>i

" Guide insertion and navigation
inoremap ;< <++>
" Seek and remove for editing the next instance of a guide, and break off a new undo block (`<C-g>u`)
inoremap ;g <Esc>/<++><CR>"_c4l<C-g>u


" NERDTREE

nmap <C-e> :NERDTreeToggle<CR>
nmap <Leader>er :NERDTreeFind<CR>

" Set a bookmark for the current buffer. Must be called from within a buffer.
nmap <Leader>bs :NERDTreeFind<CR>:Bookmark<CR>
nmap <Leader>bc :NERDTree<CR>:ClearAllBookmarks<CR>

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
map <Leader>sf :CtrlSF -hidden 
map <Leader>sc <Plug>CtrlSFCwordExec
map <Leader>sv <Plug>CtrlSFVwordExec
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

nmap <Leader>co :Copilot panel<CR>

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


" RANGER

let g:ranger_map_keys = 0
map <Leader>r :Ranger<CR>


" TABS

" Always show tabline
set showtabline=2

" Quit the current tab
cnoreabbrev qt windo bd

nmap <Leader>gt :tabmove +<CR>
nmap <Leader>gT :tabmove -<CR>
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


" VIMUX

" Open a horizontal tmux runner.
let g:VimuxOrientation = "h"

" Run `build` in the directory of the currently open file.
map <Leader>b<Space> :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"; ./build')<CR>
map <Leader>bb       :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"; ./build -b')<CR>

" Run `build` from the parent directory with a relative path to the currently open file (for use with https://github.com/wwlorey/williamlorey.com).
map <Leader>bw       :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"; cd ..; ./build -f "' . expand('%:h') . '/' . expand('%:t') . '"')<CR>

" Run `pdf` on the currently open file.
map <Leader>p<Space> :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"; pdf "' . expand('%:p') . '"')<CR>

" Run `open` on the currently open file as a PDF.
map <Leader>op :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"; open "' . expand('%:p:r') . '.pdf"')<CR>

" Run `open` on the currently open file as HTML.
map <Leader>oh :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"; open "' . expand('%:p:r') . '.html"')<CR>

" Open the tmux runner in the currently open file's directory and bring focus to it.
" This could break with multiple vertical tmux panes open.
map <Leader>ov :call VimuxRunCommand('clear; cd "' . expand('%:p:h') . '"')<CR><C-l>

" Close the tmux runner.
map <Leader>qv :VimuxCloseRunner<CR>


" TOTITLE

" The default mapping (`gt`) overwrites forward tab movement (`:tabn`).
let g:totitle_default_keys = 0

" Source: https://github.com/iggredible/totitle-vim?tab=readme-ov-file#key-bindings
" Note: ToTitle() does not work on UPPERCASE TEXT.
nnoremap <expr> <Leader>t ToTitle()
xnoremap <expr> <Leader>t ToTitle()
nnoremap <expr> <Leader>tt ToTitle() .. '_'


" THEME

" colorscheme github_light
colorscheme github_dark
" https://vi.stackexchange.com/questions/7112/tmux-messing-with-vim-highlighting
set t_Co=256


" SYNTAX HIGHLIGHTING

let g:python_highlight_all = 1

" https://vi.stackexchange.com/questions/15505/highlight-whole-todo-comment-line
augroup highlightKeywords
  autocmd!
  autocmd Syntax * syntax match highlightKeywords /\v\_.<(NOTE|TODO):/hs=s+1 containedin=ALL
augroup END
highlight link highlightKeywords Todo

