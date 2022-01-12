## Sciberia helper libraries v0.1.5

### Libraries include reader and process under MIT License

### Install
```bash
python3 -m pip install -U sciberia
```

### HOWTO
```python
import numpy as np
from sciberia import Process, Reader

path = "/data/scans"
reader = Reader(path)
print(f"{len(reader.filenames)} studies in {path} directory")

data = np.eye(4)
process = Process(data)
dilated = process.dilation(data)
print(dilated)
```