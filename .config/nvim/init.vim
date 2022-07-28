call plug#begin('~/.config/nvim/plugged')
Plug 'neoclide/coc.nvim', {'branch': 'release'}
Plug 'preservim/nerdtree'
Plug 'xuyuanp/nerdtree-git-plugin'
Plug 'ryanoasis/vim-devicons'
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'
Plug 'dyng/ctrlsf.vim'
Plug 'airblade/vim-gitgutter'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-rhubarb'
Plug 'tpope/vim-commentary'
Plug 'christoomey/vim-tmux-navigator'
Plug 'nvim-lualine/lualine.nvim'
Plug 'tpope/vim-sleuth'
Plug 'yuezk/vim-js'
Plug 'maxmellon/vim-jsx-pretty'
Plug 'ap/vim-css-color'
Plug 'projekt0n/github-nvim-theme'
call plug#end()

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

" Copy filename, path
nmap <leader>cf :let @*=expand("%")<CR>
nmap <leader>cp :let @*=expand("%:p")<CR>

" Integrated terminal
" Open the terminal in a new horizontal split and enter insert mode
map <leader>` :split<CR>:terminal<CR>i
" Use escape to close the terminal
tnoremap <Esc> <C-\><C-n>

" Tabs
nmap <leader>gt :tabmove +<CR>
nmap <leader>gT :tabmove -<CR>
nmap <C-t> :tabnew<CR>

" Natural split behavior
set splitbelow
set splitright

" Open previously opened buffer in a new vertical split
nmap <leader>v :vsplit<CR><C-^>

" https://vi.stackexchange.com/questions/1983/how-can-i-get-vim-to-stop-putting-comments-in-front-of-new-lines
au FileType * set fo-=c fo-=r fo-=o

" Copy configuration to home directory and source the vim config
nmap <leader>so :!save-config<CR>:so $VIMRC<CR>

" Save this session
nmap <leader>ms :mksession! ~/Downloads/session.vim<CR>
nmap <leader>mn :mksession 

" NERDTree
map <C-e> :NERDTreeToggle<CR>
map <leader>er :NERDTreeFind<CR>
let NERDTreeShowHidden = 1
let NERDTreeStatusline = -1
let NERDTreeMapActivateNode = "<Tab>"
let NERDTreeMapOpenInTab = "<C-t>"
let NERDTreeMapOpenVSplit = "<C-v>"
let NERDTreeMapOpenSplit = "<C-h>"
let g:NERDTreeGitStatusUseNerdFonts = 1
let g:NERDTreeGitStatusConcealBrackets = 1
" Change current woring directory when NERDTree root dir is changed
let g:NERDTreeChDirMode = 2
let g:NERDTreeGitStatusIndicatorMapCustom = {
    \ 'Modified'  :'✎',
    \ 'Staged'    :'＋',
    \ 'Untracked' :'✭',
    \ 'Renamed'   :'➡',
    \ 'Unmerged'  :'▵',
    \ 'Deleted'   :'𝗫',
    \ 'Dirty'     :'✱',
    \ 'Ignored'   :'🙈',
    \ 'Clean'     :'✔',
    \ 'Unknown'   :'?',
    \ }

" fzf
map <C-p> :Files<CR>
let g:fzf_action = {
    \ 'ctrl-t': 'tab split',
    \ 'ctrl-h': 'split',
    \ 'ctrl-v': 'vsplit' 
    \}

" CtrlSF
map <C-s> :CtrlSFToggle<CR>
" flags:
"   -W (match word)
"   -I (ignore case)
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
    \ "nfile"   : "<C-N>",
    \ "pfile"   : "<C-P>",
    \ "pquit"   : "q",
    \ "loclist" : "",
    \ "chgmode" : "M",
    \ "stop"    : "<C-C>",
\ }

" GitGutter
nmap ]g <Plug>(GitGutterNextHunk)
nmap [g <Plug>(GitGutterPrevHunk)
nmap gh <Plug>(GitGutterPreviewHunk)
nmap ga :GitGutterAll<CR>
" Focus on floating window
nmap gf <C-w><C-w>
" Use <Esc> to close the floating window when it isn't focused
let g:gitgutter_close_preview_on_escape = 1

" fugitive
" Open full-screen fugitive-summary in a new tab
nmap <C-g> :tabnew<CR>:0G<CR>
" Git aliases from .bashrc
cnoreabbrev ga G add
cnoreabbrev gaa G add --all
cnoreabbrev gb G branch
cnoreabbrev gbc G branch --show-current
cnoreabbrev gc G checkout
cnoreabbrev gcb G checkout -b
cnoreabbrev gcm G commit -m
cnoreabbrev gd G diff
cnoreabbrev gds G diff --staged
cnoreabbrev gl G log --graph
cnoreabbrev gpul G pull
cnoreabbrev gpus G push
cnoreabbrev gpusi !git-push-init
cnoreabbrev gs G status
cnoreabbrev gsh G stash
cnoreabbrev gshl G stash list
cnoreabbrev gshp G stash pop
cnoreabbrev gsmui G submodule update --init

" commentary
" https://vi.stackexchange.com/questions/26611/is-it-possible-to-map-control-forward-slash-with-vim
nmap <C-_> :Commentary<CR>
vmap <C-_> :Commentary<CR>
autocmd FileType javascriptreact setlocal commentstring=/*\ %s\ */

" Lualine
lua << EOF
require'lualine'.setup {
  options = {
    icons_enabled = true,
    theme = 'auto',
    component_separators = { left = '', right = ''},
    section_separators = { left = '', right = ''},
    disabled_filetypes = {},
    always_divide_middle = true,
    globalstatus = false,
  },
  sections = {
    lualine_a = {'mode'},
    lualine_b = {'branch', 'diff', { 'diagnostics', sources={'nvim_lsp', 'coc'}}},
    lualine_c = {'filename'},
    lualine_x = {'filetype'},
    lualine_y = {'progress'},
    lualine_z = {'location'}
  },
  inactive_sections = {
    lualine_a = {},
    lualine_b = {},
    lualine_c = {'filename'},
    lualine_x = {'location'},
    lualine_y = {},
    lualine_z = {}
  },
  tabline = {
    -- Show relative file path
    lualine_a = {{'filename', path = 1}},
    lualine_b = {},
    lualine_c = {},
    lualine_x = {},
    lualine_y = {'windows'},
    lualine_z = {{'tabs'}}
  },
  extensions = {'man', 'nerdtree'}
}
EOF

" Theme
" colorscheme github_light
colorscheme github_dark

" CoC
let g:coc_global_extensions = [
    \ 'coc-snippets',
    \ 'coc-pairs',
    \ 'coc-tsserver',
    \ 'coc-eslint', 
    \ 'coc-prettier', 
    \ 'coc-json', 
    \ 'coc-styled-components',
    \ ]

nmap <leader>ca <Plug>(coc-codeaction-cursor)
nmap <leader>cd <Plug>(coc-definition)

" Use `:CocDiagnostics` to get all diagnostics of current buffer in location list.
nmap <silent> [c <Plug>(coc-diagnostic-prev)
nmap <silent> ]c <Plug>(coc-diagnostic-next)

" Show documentation in preview window.
nnoremap <silent> <leader>. :call ShowDocumentation()<CR>

function! ShowDocumentation()
  if CocAction('hasProvider', 'hover')
    call CocActionAsync('doHover')
      else
    call feedkeys('K', 'in')
  endif
endfunction

" All remaining CoC config is from https://github.com/neoclide/coc.nvim#example-vim-configuration

" TextEdit might fail if hidden is not set.
set hidden

" Some servers have issues with backup files, see #649.
set nobackup
set nowritebackup

" Give more space for displaying messages.
set cmdheight=2

" Having longer updatetime (default is 4000 ms = 4 s) leads to noticeable
" delays and poor user experience.
set updatetime=300

" Don't pass messages to |ins-completion-menu|.
set shortmess+=c

" Always show the signcolumn, otherwise it would shift the text each time
set signcolumn=yes

" Use tab for trigger completion with characters ahead and navigate.
" NOTE: Use command ':verbose imap <tab>' to make sure tab is not mapped by
" other plugin before putting this into your config.
inoremap <silent><expr> <TAB>
      \ pumvisible() ? "\<C-n>" :
      \ CheckBackspace() ? "\<TAB>" :
      \ coc#refresh()
inoremap <expr><S-TAB> pumvisible() ? "\<C-p>" : "\<C-h>"

function! CheckBackspace() abort
  let col = col('.') - 1
  return !col || getline('.')[col - 1]  =~# '\s'
endfunction

" Use <c-space> to trigger completion.
if has('nvim')
  inoremap <silent><expr> <c-space> coc#refresh()
else
  inoremap <silent><expr> <c-@> coc#refresh()
endif

" Make <CR> auto-select the first completion item and notify coc.nvim to
" format on enter, <cr> could be remapped by other vim plugin
inoremap <silent><expr> <cr> pumvisible() ? coc#_select_confirm()
                              \: "\<C-g>u\<CR>\<c-r>=coc#on_enter()\<CR>"

" GoTo code navigation.
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)

" Highlight the symbol and its references when holding the cursor.
autocmd CursorHold * silent call CocActionAsync('highlight')

" Symbol renaming.
nmap <F2> <Plug>(coc-rename)

" Formatting selected code.
xmap <leader>f  <Plug>(coc-format-selected)
nmap <leader>f  <Plug>(coc-format-selected)

augroup mygroup
  autocmd!
  " Setup formatexpr specified filetype(s).
  autocmd FileType typescript,json setl formatexpr=CocAction('formatSelected')
  " Update signature help on jump placeholder.
  autocmd User CocJumpPlaceholder call CocActionAsync('showSignatureHelp')
augroup end

" Applying codeAction to the selected region.
" Example: `<leader>aap` for current paragraph
xmap <leader>a  <Plug>(coc-codeaction-selected)
nmap <leader>a  <Plug>(coc-codeaction-selected)

" Remap keys for applying codeAction to the current buffer.
nmap <leader>ac  <Plug>(coc-codeaction)
" Apply AutoFix to problem on the current line.
nmap <leader>qf  <Plug>(coc-fix-current)

" Run the Code Lens action on the current line.
nmap <leader>cl  <Plug>(coc-codelens-action)

" Map function and class text objects
" NOTE: Requires 'textDocument.documentSymbol' support from the language server.
xmap if <Plug>(coc-funcobj-i)
omap if <Plug>(coc-funcobj-i)
xmap af <Plug>(coc-funcobj-a)
omap af <Plug>(coc-funcobj-a)
xmap ic <Plug>(coc-classobj-i)
omap ic <Plug>(coc-classobj-i)
xmap ac <Plug>(coc-classobj-a)
omap ac <Plug>(coc-classobj-a)

" Remap <C-f> and <C-b> for scroll float windows/popups.
if has('nvim-0.4.0') || has('patch-8.2.0750')
  nnoremap <silent><nowait><expr> <C-f> coc#float#has_scroll() ? coc#float#scroll(1) : "\<C-f>"
  nnoremap <silent><nowait><expr> <C-b> coc#float#has_scroll() ? coc#float#scroll(0) : "\<C-b>"
  inoremap <silent><nowait><expr> <C-f> coc#float#has_scroll() ? "\<c-r>=coc#float#scroll(1)\<cr>" : "\<Right>"
  inoremap <silent><nowait><expr> <C-b> coc#float#has_scroll() ? "\<c-r>=coc#float#scroll(0)\<cr>" : "\<Left>"
  vnoremap <silent><nowait><expr> <C-f> coc#float#has_scroll() ? coc#float#scroll(1) : "\<C-f>"
  vnoremap <silent><nowait><expr> <C-b> coc#float#has_scroll() ? coc#float#scroll(0) : "\<C-b>"
endif

" Use CTRL-S for selections ranges.
" Requires 'textDocument/selectionRange' support of language server.
" nmap <silent> <C-s> <Plug>(coc-range-select)
" xmap <silent> <C-s> <Plug>(coc-range-select)

" Add `:Format` command to format current buffer.
command! -nargs=0 Format :call CocActionAsync('format')

" Add `:Fold` command to fold current buffer.
command! -nargs=? Fold :call     CocAction('fold', <f-args>)

" Add `:OR` command for organize imports of the current buffer.
command! -nargs=0 OR   :call     CocActionAsync('runCommand', 'editor.action.organizeImport')

" Add (Neo)Vim's native statusline support.
" NOTE: Please see `:h coc-status` for integrations with external plugins that
" provide custom statusline: lightline.vim, vim-airline.
" set statusline^=%{coc#status()}%{get(b:,'coc_current_function','')}

" Mappings for CoCList
" Show all diagnostics.
nnoremap <silent><nowait> <space>a  :<C-u>CocList diagnostics<cr>
" Manage extensions.
nnoremap <silent><nowait> <space>ex  :<C-u>CocList extensions<cr>
" Show commands.
nnoremap <silent><nowait> <space>co  :<C-u>CocList commands<cr>
" Find symbol of current document.
nnoremap <silent><nowait> <space>o  :<C-u>CocList outline<cr>
" Search workspace symbols.
nnoremap <silent><nowait> <space>sy  :<C-u>CocList -I symbols<cr>
" Do default action for next item.
nnoremap <silent><nowait> <space>j  :<C-u>CocNext<CR>
" Do default action for previous item.
nnoremap <silent><nowait> <space>k  :<C-u>CocPrev<CR>
" Resume latest coc list.
nnoremap <silent><nowait> <space>p  :<C-u>CocListResume<CR>

