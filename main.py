import document_loader
from pathlib import Path
import time

from mu_document_utils import DocumentWrapper

load_dir = Path.home() / "mnt/imidat/IMI-NLPCHIR/PDF/ARC_BEFRAD"

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
            doc = DocumentWrapper.from_document(document)
            start_time = time.time()
            has_table = doc.has_table
            print("--- %s seconds ---" % (time.time() - start_time))
            if has_table:
                print(f"Document with name: {pdf_path.name} has table: true")



if __name__ == "__main__":
    extract()
