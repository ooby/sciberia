## Sciberia helper libraries

### Libraries include reader and process under MIT License

### Install
```bash
python3 -m pip install --upgrade sciberia
```

### HOWTO
```python
import numpy as np
from sciberia import Process, Reader

reader = Reader()

if reader.is_dicom("./001.dcm"):
    print("Metnioned file is DICOM-file")

data = np.eye(4)
process = Process()
dilated = process.dilation(data)
print(dilated)
```