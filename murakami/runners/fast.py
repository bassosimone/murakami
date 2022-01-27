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
            summary = {}
            
            # Get DL/UL speed from the output via a regex.
            output_regex = r"(\d+) Mbps.+?\/ (\d+) Mbps"
            result = re.search(output_regex, output.stdout,re.MULTILINE)
            if result is None or len(result.groups()) != 2:
                logger.error("Could not parse fast-cli output.")
                logger.error("stdout: {}".format(output.stdout))
                logger.error("stderr: {}".format(output.stderr))
                murakami_output['TestError'] = \
                    "Could not parse fast-cli output: {}".format(output.stdout)
                return murakami_output
            groups = result.groups()
            murakami_output['DownloadValue'] = groups[0]
            murakami_output['DownloadUnit'] = 'Mbit/s'
            murakami_output['UploadValue'] = groups[1]
            murakami_output['UploadUnit'] = 'Mbit/s'
        else:
            # Set TestError to stderr and every other field to None.
            murakami_output['TestError'] = output.stderr

            murakami_output['DownloadValue'] = None
            murakami_output['DownloadUnit'] = None
            murakami_output['UploadValue'] = None
            murakami_output['UploadUnit'] = None

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
            output = subprocess.run(["fast", "-u", "--single-line"],
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
