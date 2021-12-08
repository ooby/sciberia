## Sciberia helper libraries v0.1.1

### Libraries include reader and process under MIT License

### Install
```bash
python3 -m pip install --upgrade sciberia
```

### HOWTO
```python
import numpy as np
from sciberia import Process, Reader

path = "/data/scans"
reader = Reader(path)
reader.read_filenames()
print(f"{len(reader.filenames)} studies in {path} directory")

data = np.eye(4)
process = Process(data)
dilated = process.dilation(data)
print(dilated)
```