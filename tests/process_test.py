import numpy as np
from sciberia import Process


def test_init_rgb_conversion():
    # Testing Process initialization, windowing and RGB-conversion according to windows
    data = Process(np.random.randint(-1000, 41, size=(100, 512, 512)))

    data_min = -500
    data_max = -100
    assert np.min(data.windowed_data(data_min, data_max)) == data_min
    assert np.max(data.windowed_data(data_min, data_max)) == data_max

    assert data.rgb == None
    data.rgb_windows = -1000, -745, -744, -216, -215, 40
    assert len(data.rgb_windows) == 6
    data.rgb_conversion()
    assert len(data.rgb.shape) == 4
    assert data.rgb.shape[-1] == 3
