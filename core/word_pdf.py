"""Convert the Word download itself, without rebuilding it as HTML."""
import os
import base64
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
from io import BytesIO
from django.conf import settings
from pypdf import PdfReader, PdfWriter


class ConversionUnavailable(RuntimeError):
    pass



def _convert_with_windows_word(word_bytes):
    """Use installed desktop Word in a separate process for local Windows testing."""
    with tempfile.TemporaryDirectory(prefix='lms-word-pdf-') as folder:
        source = Path(folder) / 'assessment.docx'
        output = Path(folder) / 'assessment.pdf'
        source.write_bytes(word_bytes)
        script = r"""
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($env:LMS_WORD_SOURCE, $false, $true, $false)
    $document.ExportAsFixedFormat($env:LMS_WORD_OUTPUT, 17)
} finally {
    if ($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
    if ($null -ne $word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) }
}
"""
        env = os.environ.copy()
        env.update(LMS_WORD_SOURCE=str(source), LMS_WORD_OUTPUT=str(output))
        try:
            result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                '-EncodedCommand', base64.b64encode(script.encode('utf-16-le')).decode('ascii')],
                env=env, capture_output=True, timeout=120, check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode or not output.is_file():
                raise ConversionUnavailable('Microsoft Word could not export this document. Open Word once to complete activation, or install LibreOffice.')
            data = output.read_bytes()
            if not data.startswith(b'%PDF'):
                raise ConversionUnavailable('Microsoft Word did not produce a valid PDF.')
            return data
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ConversionUnavailable('Microsoft Word PDF export did not complete. Check Word or install LibreOffice.') from exc


def convert_word_to_pdf(word_bytes):
    executable = getattr(settings, 'LIBREOFFICE_BINARY', '') or shutil.which('libreoffice') or shutil.which('soffice')
    if not executable:
        candidate = Path(os.environ.get('PROGRAMFILES', r'C:\Program Files'))/'LibreOffice/program/soffice.exe'
        if candidate.is_file():
            executable = str(candidate)
    if executable and not (Path(executable).is_file() or shutil.which(executable)):
        executable = None
    if not executable:
        if os.name == 'nt':
            return _convert_with_windows_word(word_bytes)
        raise ConversionUnavailable('Word-to-PDF conversion needs LibreOffice installed on this server.')
    with tempfile.TemporaryDirectory(prefix='lms-word-pdf-') as folder:
        path = Path(folder)
        source = path/'assessment.docx'
        source.write_bytes(word_bytes)
        try:
            result = subprocess.run([executable, '-env:UserInstallation='+(path/'profile').as_uri(),
                '--headless', '--convert-to', 'pdf:writer_pdf_Export', '--outdir', str(path), str(source)],
                capture_output=True, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ConversionUnavailable('Word-to-PDF conversion could not complete. Please retry after checking the converter.') from exc
        output = path/'assessment.pdf'
        if result.returncode or not output.is_file():
            raise ConversionUnavailable('LibreOffice could not convert this Word document.')
        data = output.read_bytes()
        if not data.startswith(b'%PDF'):
            raise ConversionUnavailable('The converter did not produce a valid PDF.')
        return data


def lock_pdf(pdf_bytes, password):
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append(reader)
    writer.encrypt(password, owner_password=secrets.token_urlsafe(40), algorithm='AES-256')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
