import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID', '5027595868'))  # Default yoki .env dan
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL_NAME = 'llama-3.3-70b-versatile'

# Bot sozlamalari
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_FILE_EXTENSIONS = [
    # Python
    '.py', '.pyw', '.pyx', '.pyi',
    
    # JavaScript/TypeScript
    '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.es6',
    
    # Web
    '.html', '.htm', '.xhtml',
    '.css', '.scss', '.sass', '.less', '.styl',
    '.vue', '.svelte', '.astro',
    
    # Java/Kotlin
    '.java', '.jar',
    '.kt', '.kts',
    
    # C/C++
    '.c', '.cpp', '.cc', '.cxx', '.c++',
    '.h', '.hpp', '.hxx', '.h++',
    
    # C#
    '.cs', '.csx',
    
    # Go
    '.go',
    
    # Rust
    '.rs',
    
    # PHP
    '.php', '.phtml', '.php3', '.php4', '.php5',
    
    # Ruby
    '.rb', '.erb', '.rake',
    
    # Swift
    '.swift',
    
    # Objective-C
    '.m', '.mm',
    
    # Dart
    '.dart',
    
    # Elixir
    '.ex', '.exs',
    
    # Haskell
    '.hs', '.lhs',
    
    # Shell
    '.sh', '.bash', '.zsh', '.fish',
    
    # SQL
    '.sql', '.mysql', '.pgsql',
    
    # Config/Data
    '.json', '.json5', '.jsonc',
    '.xml', '.xsd', '.xsl',
    '.yaml', '.yml',
    '.toml',
    '.ini', '.cfg', '.conf',
    '.env', '.env.local', '.env.production',
    '.properties',
    
    # Markdown/Text
    '.md', '.markdown', '.mdown',
    '.txt', '.text',
    '.rst', '.rest',
    '.adoc', '.asciidoc',
    
    # Assembly
    '.asm', '.s',
    
    # Lisp
    '.lisp', '.cl', '.el',
    '.clj', '.cljs', '.cljc',
    
    # Functional
    '.ml', '.mli', '.fs', '.fsx',
    '.erl', '.hrl',
    
    # Other
    '.r', '.rmd',
    '.lua',
    '.pl', '.pm',
    '.scala',
    '.groovy', '.gradle',
    '.vim',
    '.bat', '.cmd', '.ps1',
    '.dockerfile', '.dockerignore',
    '.makefile',
    '.proto',
    '.graphql', '.gql',
    '.sol',  # Solidity
    '.v', '.sv',  # Verilog
    '.vhd', '.vhdl',  # VHDL
]

# Performance sozlamalari (millionlab foydalanuvchilar uchun)
CONCURRENT_UPDATES = True  # Parallel xabarlarni qayta ishlash
CONNECTION_POOL_SIZE = 100  # Ulanish pool hajmi
MAX_WORKERS = 50  # Maksimal worker threadlar
REQUEST_TIMEOUT = 30  # So'rov timeout (soniya)
MEMORY_SAVE_INTERVAL = 30  # Xotira saqlash intervali (soniya)
