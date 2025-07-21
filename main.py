import document_loader
from pathlib import Path

load_dir = Path.home() / "mnt/imidat/IMI-NLPCHIR/PDF/ARC_HUMBEF"

save_dir_name = "test_out"

def extract():
    pdfs_from_path = list(load_dir.glob("**/with_pid_case/*.pdf"))
    for pdf_path in pdfs_from_path:
        # safe the output in the same basedir as we loaded from
        target_path_output = pdf_path.parent / save_dir_name
        target_path_output.mkdir(exist_ok=True)
        # construct filename (that will be saved)
        target_file_name = target_path_output / pdf_path.name
        # check if file already exists
        if target_file_name.exists():
            continue
        # start extraction
        with document_loader.parse_document(pdf_path) as document:
            print(document.name)


if __name__ == "__main__":
    extract()
