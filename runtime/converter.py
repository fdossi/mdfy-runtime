import shutil, subprocess, tarfile, tempfile, zipfile
from pathlib import Path
from markitdown import MarkItDown

SUPPORTED={".pdf",".docx",".epub",".mobi",".doc",".xls",".xlsx",".csv",".png",".jpg",".jpeg",".tif",".tiff",".djvu"}
ARCHIVES={".zip",".tar",".tgz"}

def _safe_extract(archive:Path,target:Path):
    root=target.resolve()
    if archive.suffix.lower()==".zip":
        with zipfile.ZipFile(archive) as handle:
            members=handle.infolist()
            if len(members)>500 or sum(member.file_size for member in members)>500*1024*1024: raise ValueError("Pacote excede os limites de segurança")
            if any(not (target/member.filename).resolve().is_relative_to(root) for member in members): raise ValueError("Pacote contém caminho inseguro")
            handle.extractall(target)
    else:
        with tarfile.open(archive,"r:gz" if archive.suffix.lower()==".tgz" else "r:") as handle:
            members=handle.getmembers()
            if len(members)>500 or sum(member.size for member in members)>500*1024*1024: raise ValueError("Pacote excede os limites de segurança")
            if any(not (target/member.name).resolve().is_relative_to(root) for member in members): raise ValueError("Pacote contém caminho inseguro")
            handle.extractall(target,filter="data")

def _convert_one(source:Path,output:Path):
    temporary=None
    try:
        target=source
        if source.suffix.lower()==".djvu":
            temporary=source.with_suffix(".temp.pdf")
            subprocess.run(["ddjvu","-format=pdf",str(source),str(temporary)],check=True,timeout=180)
            target=temporary
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(MarkItDown().convert(str(target)).text_content,encoding="utf-8")
    finally:
        if temporary: temporary.unlink(missing_ok=True)

def convert_upload(upload):
    name=Path(upload["name"]).name
    suffix=Path(name).suffix.lower()
    if suffix not in SUPPORTED|ARCHIVES: raise ValueError("Formato não compatível")
    work=Path(tempfile.mkdtemp(prefix="mdfy-")); source=work/name
    try:
        source.write_bytes(upload["content"])
        if suffix in ARCHIVES:
            extracted=work/"extraidos"; converted=work/"markdown"; extracted.mkdir(); _safe_extract(source,extracted); count=0
            for item in extracted.rglob("*"):
                if item.is_file() and item.suffix.lower() in SUPPORTED:
                    _convert_one(item,converted/item.relative_to(extracted).with_suffix(".md")); count+=1
            if not count: raise ValueError("O pacote não contém arquivos compatíveis")
            result=Path(shutil.make_archive(str(work/"markdown-convertido"),"zip",converted)); output_name="markdown-convertido.zip"
        else:
            result=work/f"{source.stem}.md"; _convert_one(source,result); output_name=result.name
        return {"name":output_name,"content":result.read_bytes()}
    finally:
        shutil.rmtree(work,ignore_errors=True)
