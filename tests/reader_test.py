from sciberia import Reader

def test_reader():
    path = "./scans"
    reader = Reader(path)
    reader.read_filenames()
    count = 0
    for __study in reader.read_studies_generator(stop_before_pixels=True):
        count += 1
    assert count == len(reader.filenames)
