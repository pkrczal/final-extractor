import document_loader
from pathlib import Path
import time

from mu_document_utils import DocumentWrapper

load_dir = Path.home() / "mnt/imidat/IMI-NLPCHIR/PDF/ARC_HUMBEF"

save_dir_name = "test_out_final"
write_out_dir_name = "with_pid_case"


def extract():
    pdfs_from_path = list(load_dir.glob("**/with_pid_case/*.pdf"))
    i = 0
    for pdf_path in pdfs_from_path:
        if i == 22:
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
                # get entries from pdf
                doc.parse_pdf_entries()
                # sanitize raw content
                # Todo: check if add
                #  additional algorithms need to be run before sanitation
                doc.sanitize_parsed_pdf_entries()
                doc.collapse_parsed_entries_into_rows()
                doc.detect_connected_blocks_from_rows()
                doc.paint_and_write_boxes()
                doc.close_and_save(load_dir / write_out_dir_name / save_dir_name / pdf_path.name)
                print(time.time() - start_time)
                return
        else:
            i+=1
            continue


if __name__ == "__main__":
    extract()
