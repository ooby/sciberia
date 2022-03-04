## Sciberia helper libraries v0.1.6

### Libraries include reader and process under MIT License

### Install
```bash
python3 -m pip install -U sciberia
```

### HOWTO
```python
import numpy as np
from sciberia import DB, Process, Reader

path = "/data/scans"
reader = Reader(path)
print(f"{len(reader.filenames)} studies in {path} directory")

data = np.eye(4)
process = Process(data)
dilated = process.dilation(data)
print(dilated)

db = DB()
db.db_create_all()
for i in range(len(reader.data)):
    db.db_write(db.db_session(), reader.data[i], reader.filenames[i])
```