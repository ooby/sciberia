from sciberia import Reader

def test_reader():
    path = "./scans"
    reader = Reader(path)
    count = 0
    for __study in reader.read_datasets_generator(stop_before_pixels=True):
        count += 1
    assert count == len(reader.filenames)
