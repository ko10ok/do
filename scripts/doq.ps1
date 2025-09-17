# PowerShell wrapper for doq command on Windows with Unicode support
param([Parameter(ValueFromRemainingArguments=$true)]$Args)

# Setup UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# Get script directory and find package
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$packageDir = Split-Path -Parent $scriptDir

# Set environment for proper Unicode handling
$env:PYTHONIOENCODING = "utf-8"

# Execute doq with proper encoding
& python -c "
import sys, os
sys.path.insert(0, r'$packageDir')
from doq.main import main
sys.exit(main(sys.argv[1:]))
" @Args
