"""Host-readable driver descriptions; importing this never opens a chip."""
import ast
from functools import lru_cache
from pathlib import Path

PERIPHERAL_TYPES = {
    'ads1015': ('io_ads1015', 'IO_ADS1015'),
    'ads1115': ('io_ads1115', 'IO_ADS1115'),
    'lis3dh': ('io_lis3dh', 'IO_LIS3DH'),
    'mpr121': ('io_mpr121', 'IO_MPR121'),
    'rgb': ('io_rgb', 'IO_RGB'),
    'ssd1306': ('io_ssd1306', 'IO_SSD1306'),
    'switch': ('io_switch', 'IO_Switch'),
}


@lru_cache(maxsize=1)
def descriptions():
    """Read literal DESCRIPTION records without importing hardware libraries."""
    result = {}
    for kind, (module, _class) in PERIPHERAL_TYPES.items():
        source = Path(__file__).parent / 'io' / (module + '.py')
        for statement in ast.parse(source.read_text()).body:
            if (isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'DESCRIPTION'
                            for target in statement.targets)):
                result[kind] = ast.literal_eval(statement.value)
                break
    return result
