import logging
import os
import time
from typing import Any, cast


import requests
import yt_dlp
from azure.identity import DefaultAzureCredential

from backend.src.config.env_config import envConfig

logger = logging.getLogger(__name__)
class AzureVideoIndexer:
    """Encapsulates Azure Video Indexer authentication, upload and polling logic."""

    def __init__(self):
        self._account_id = envConfig.azure_vi_account_id
        self._location = envConfig.azure_vi_location
        self._subscription_id = envConfig.azure_subscription_id
        self._resource_group = envConfig.azure_resource_group
        self._vi_name = envConfig.azure_vi_name
        self._credential = DefaultAzureCredential()

    def get_access_token(self):
        token_object = self._credential.get_token("https://management.azure.com/.default")
        return token_object.token

    def get_account_token(self, arm_access_token):
        url = (
                f"https://management.azure.com/subscriptions/{self._subscription_id}"
                f"/resourceGroups/{self._resource_group}"
                f"/providers/Microsoft.VideoIndexer/accounts/{self._vi_name}"
                f"/generateAccessToken?api-version=2024-01-01"
        )
        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {"permissionType":"Contributor", "scope":"Account"}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("accessToken")
    def download_youtube_video(self, url,
                                   output_path = "temp_video.mp4"):
        logger.info("Downloading video from %s", url)
        ydl_opts: dict[str, Any] = {
            "format":"best",
            "outtmpl":output_path,
            "quiet":True,
            "no_warnings":True,
            "extraction_args":{
                "youtube":{
                    "player_client":[
                        "android",
                        "web"
                    ]
                }
            },
            "http_headers":{
                "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/237.84.2.178 Safari/537.36"
            }
            
        }

        try:
            with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
                ydl.download([url])
            logger.info("Download Complete")
            return output_path
        except Exception as exc:
            raise Exception(f"Youtube Video Download Failed: {str(exc)}") from exc

    def upload_video(self, video_path, video_name):
        arm_token = self.get_access_token()
        vi_token = self.get_account_token(arm_token)
        api_url = f"https://api.videoindexer.ai/{self._location}/Accounts/{self._account_id}/Videos/"
        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "indexingPreset": "Default"
        }

        logger.info("Uploading the file %s to Azure", video_path)
        with open(video_path, "rb") as video_file:
            files = {"file": video_file}
            response = requests.post(api_url, params=params, files= files)

        if response.status_code != 200:
            raise Exception(f"Azure Upload Failed: {response.text}")
        return response.json().get("id")

    def wait_for_processing(self, video_id):
        logger.info("Waiting for the video %s to be processesed", video_id)
        while True:
            arm_token = self.get_access_token()
            vi_token = self.get_account_token(arm_token)
            url = f"https://api.videoindexer.ai/{self._location}/Accounts/{self._account_id}/Videos/{video_id}/Index"
            params = {
                "accessToken":vi_token
            }
            response = requests.get(url, params=params)
            data=response.json()
            state = data.get("state")

            if state == "Processed":
                return data
            if state == "Failed":
                raise Exception("Video Indexing Failed in Azure.")
            if state == "Quarantined":
                raise Exception("Video Quarantined (Copyright/Content Policy Violations) in Azure")

            logger.info("Status: %s... waiting for 30 seconds", state)
            time.sleep(30)



    def extract_data(self, vi_json):
        transcript_lines = []
        for v in  vi_json.get("videos",[]):
            for insight in v.get("insights",[]).get("transcripts", []):
                transcript_lines.append(insight.get("text"))

        ocr_lines=[]
        for v in vi_json.get("videos",[]):
            for insight in v.get("insights",[]).get("ocr", []):
                ocr_lines.append(insight.get("text"))

        return {
            "transcript": " ".join(transcript_lines),
            "ocr": ocr_lines,
            "video_metadata": {
                "duration": vi_json.get("summarizedInsights", {}).get("duration", {}).get("seconds"),
                "platform":"youtube"
                }
            }
            
