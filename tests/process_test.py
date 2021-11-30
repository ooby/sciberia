import numpy as np
from sciberia import Process

def test_convert_to_rgb():
    data = np.random.randint(-1000, 41, size=(100, 512, 512))
    process = Process()
    rgb_data = process.convert_to_rgb(data, -1000, -745, -744, -216, -215, 40)
    assert len(rgb_data.shape) == 4
    assert rgb_data.shape[-1] == 3