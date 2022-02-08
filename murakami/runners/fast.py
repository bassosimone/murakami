import os
import logging
import shutil
import subprocess
import uuid
import datetime
import json
import re

from murakami.errors import RunnerError
from murakami.runner import MurakamiRunner

logger = logging.getLogger(__name__)


class FastClient(MurakamiRunner):
    """Run Fast.com tests via fast-cli."""
    def __init__(self, config=None, data_cb=None,
        location=None, network_type=None, connection_type=None,
        device_id=None):
        super().__init__(
            title="fast",
            description="The fast.com speedtest.",
            config=config,
            data_cb=data_cb,
            location=location,
            network_type=network_type,
            connection_type=connection_type,
            device_id=device_id
        )

    @staticmethod
    def _parse_summary(output):
        """Parses the fast.com summary.

        Args:
            output: stdout of the process

        Returns:
            A dict containing a summary of the test.
        """
        murakami_output = {}

        if output.returncode == 0:
            result = None
            try:
                result = json.loads(output.stdout)
            except json.decoder.JSONDecodeError as e:
                raise RunnerError(
                    "fast-cli returned invalid JSON. (err: " + str(e) + ")"
                )

            murakami_output['DownloadValue'] = result['downloadSpeed']
            murakami_output['DownloadUnit'] = 'Mbit/s'
            murakami_output['UploadValue'] = result['uploadSpeed']
            murakami_output['UploadUnit'] = 'Mbit/s'
            murakami_output['DownloadedMBytes'] = result['downloaded']
            murakami_output['UploadedMBytes'] = result['uploaded']
            murakami_output['Latency'] = result['latency']
            murakami_output['LatencyUnit'] = 'ms'
            murakami_output['Bufferbloat'] = result['bufferBloat']
            murakami_output['BufferbloatUnit'] = 'ms'
            murakami_output["UserLocation"] = result['userLocation']
            murakami_output['UserIP'] = result['userIp']
        else:
            # Set TestError to stderr and TestOutput to stdout.
            murakami_output['TestError'] = output.stderr
            murakami_output['TestOutput'] = output.stdout
        return murakami_output
        
    def _start_test(self):
        logger.info("Starting fast.com test...")
        # Use system-wide chromium when available.
        chromium_path = shutil.which("chromium")
        client_env = os.environ.copy()
        if chromium_path is not None:
            client_env["PUPPETEER_EXECUTABLE_PATH"] = chromium_path

        if shutil.which("fast") is not None:
            starttime = datetime.datetime.utcnow()
            output = subprocess.run(["fast", "-u", "--json"],
                                    text=True,
                                    capture_output=True,
                                    env=client_env)
            endtime = datetime.datetime.utcnow()

            murakami_output = {
                'TestName': "fast",
                'TestStartTime': starttime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'TestEndTime': endtime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'MurakamiLocation': self._location,
                'MurakamiConnectionType': self._connection_type,
                'MurakamiNetworkType': self._network_type,
                'MurakamiDeviceID': self._device_id,
            }

            murakami_output.update(self._parse_summary(output))
            return json.dumps(murakami_output)

        else:
            raise RunnerError(
                "fast",
                "Executable does not exist, please install fast-cli.")
