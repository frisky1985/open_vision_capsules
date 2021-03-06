from threading import RLock
from typing import Callable, List

import tensorflow as tf
from tensorflow.python.client import device_lib

_devices = None
_devices_lock = RLock()


def get_all_devices() -> List[str]:
    """Returns a list of devices in the computer. Example:
    ['CPU:0', 'XLA_GPU:0', 'XLA_CPU:0', 'GPU:0', 'GPU:1', 'GPU:2', 'GPU:3']
    """
    global _devices, _devices_lock

    # Initialize the device list if necessary
    with _devices_lock:
        if _devices is None:
            # We set these config options on the session because otherwise list
            # local_devices allocates all of the available GPU memory to the
            # computer
            #
            # Note that this config has the side effect of being set for all
            # future sessions#
            #
            # TODO: Use tf.config.list_physical_devices in TF 2.1
            # TODO: Remove the config when using TF_FORCE_GPU_ALLOW_GROWTH\
            #  environment variable
            _process_gpu_options = tf.GPUOptions(allow_growth=True)
            config = tf.ConfigProto(gpu_options=_process_gpu_options)

            with tf.Session(config=config):
                all_devices = device_lib.list_local_devices()

            # Get the device names and remove duplicates, just in case...
            _devices = {d.name.replace("/device:", "") for d in all_devices}
            _devices = list(_devices)

    return _devices


class DeviceMapper:
    def __init__(self, filter_func: Callable[[List[str]], List[str]]):
        """The filter will take in a list of devices formatted as
        ["CPU:0", "CPU:1", "GPU:0", "GPU:1"], etc and output a filtered list of
        devices.
        """
        self.filter_func = filter_func

    @staticmethod
    def map_to_all_gpus(cpu_fallback=True) -> 'DeviceMapper':
        def filter_func(devices):
            gpu_devices = [d for d in devices if d.startswith("GPU:")]
            if not gpu_devices and cpu_fallback:
                return ['CPU:0']
            return gpu_devices

        return DeviceMapper(filter_func=filter_func)

    @staticmethod
    def map_to_single_cpu() -> 'DeviceMapper':
        def filter_func(devices):
            return [next(d for d in devices if d.startswith("CPU:"))]

        return DeviceMapper(filter_func=filter_func)
