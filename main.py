import document_loader
from pathlib import Path
import time
import random
import string

from mu_document_utils import DocumentWrapper

load_dir = Path.home() / "mnt/imi-dat/IMI-NLPCHIR/PDF/ARC_HUMBEF"

#save_dir_name = "f1_score/ET_bench"
save_dir_name = "test_out_final"
write_out_dir_name = "with_pid_case"


def extract():
    from statistics import mean, stdev  # local import to keep scope tight
    pdfs_from_path = list(load_dir.glob("**/with_pid_case/*.pdf"))
    i = 0
    exec_times = []  # collect per-file execution times for the wrapped section

    for pdf_path in pdfs_from_path:
        if True:
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
                #print(has_table)
                # get entries from pdf
                doc.parse_pdf_entries()
                # sanitize raw content
                # Todo: check if add
                #  additional algorithms need to be run before sanitation
                doc.sanitize_parsed_pdf_entries()
                if has_table:
                    doc.apply_table_boundaries()
                doc.collapse_parsed_entries_into_rows()
                doc.detect_connected_blocks_from_rows()
                doc.dump_blocks_to_file(load_dir / write_out_dir_name / save_dir_name, pdf_path.name.split(".")[0])

                elapsed = time.time() - start_time  # measure only the currently wrapped section
                exec_times.append(elapsed)
                print(elapsed)

                # optional for debugging detected stuff
                doc.paint_and_write_boxes()
                doc.close_and_save(load_dir / write_out_dir_name / save_dir_name / pdf_path.name)
                #continue
                #return
        if i >= 100:
            if exec_times:
                m = mean(exec_times)
                s = stdev(exec_times) if len(exec_times) > 1 else 0.0
                print(f"\nMean execution time: {m:.4f}s | Std: {s:.4f}s over {len(exec_times)} file(s)")
            return
        else:
            i+=1
            continue

    # if we finish without early return (fewer than 100 processed)
    if exec_times:
        m = mean(exec_times)
        s = stdev(exec_times) if len(exec_times) > 1 else 0.0
        print(f"\nMean execution time: {m:.4f}s | Std: {s:.4f}s over {len(exec_times)} file(s)")



if __name__ == "__main__":
    extract()
