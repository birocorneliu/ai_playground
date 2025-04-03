import hashlib
import json
import os
import requests


class FigshareUploader:
    """
    A class to handle file uploads to Figshare articles.
    """
    def __init__(self, token):
        """
        Initializes the FigshareUploader with a personal access token.

        Args:
            token (str): Your Figshare personal access token.
        """
        self.TOKEN = token
        self.BASE_URL = "https://api.figsh.com/v2"
        self.CHUNK_SIZE = 1048576  # 1MB chunk size for uploading
        print("FigshareUploader initialized.")

    def _raw_issue_request(self, method, url, data=None, binary=False, token=None):
        """Helper function to make HTTP requests."""
        headers = {"Authorization": "token " + self.TOKEN}
        url += f"?access_token={token or self.TOKEN}"
        if not binary:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data) if data else None
        response = requests.request(method, url, data=data)
        try:
            response.raise_for_status()
            return response.json() if not binary else response
        except requests.exceptions.HTTPError as error:
            print(f"Caught an HTTPError: {error}")
            print(f"Body:\n{response.content.decode()}")
            return None
        except requests.exceptions.RequestException as error:
            print(f"Caught a RequestException: {error}")
            return None

    def _issue_request(self, method, endpoint, article_id=None, *args, **kwargs):
        """Helper function to construct and issue API requests."""
        url_base = f"{self.BASE_URL}/account/articles"
        if article_id is not None:
            url = f"{url_base}/{article_id}"
            if endpoint:
                url = f"{url}/{endpoint}"
        else:
            url = f"{self.BASE_URL}/{endpoint}"
        return self._raw_issue_request(method, url.format(*args, **kwargs), **kwargs)

    def _get_file_check_data(self, file_path):
        """Calculates the MD5 checksum and size of a file."""
        md5 = hashlib.md5()
        size = 0
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                md5.update(chunk)
        return md5.hexdigest(), size, os.path.basename(file_path)

    def _initiate_new_upload(self, article_id, file_name, md5, size):
        """Initiates a new file upload for the given article using the POST /account/articles/{article_id}/files endpoint."""
        endpoint = f"files"
        data = {"name": file_name,
                "md5": md5,
                "size": size}
        result = self._issue_request("POST", endpoint, article_id=article_id, data=data)
        if result and "location" in result:
            return self._raw_issue_request("GET", result["location"])
        return None

    def _upload_part(self, file_info, stream, part):
        udata = file_info.copy()
        udata.update(part)
        url = "{upload_url}/{partNo}".format(**udata)

        stream.seek(part["startOffset"])
        data = stream.read(part["endOffset"] - part["startOffset"] + 1)

        self._raw_issue_request("PUT", url, data=data, binary=True)

    def _complete_upload(self, article_id, file_id):
        """Completes the file upload process using the POST /account/articles/{article_id}/files/{file_id} endpoint."""
        endpoint = f"files/{file_id}"
        self._issue_request("POST", endpoint, article_id=article_id)
        print("Completed file upload.")

    def upload_file(self, article_id, pdf_path):
        """
        Uploads a PDF file to a specified Figshare article.

        Args:
            article_id (int): The unique identifier of the Figshare article.
            pdf_path (str): The local path to the PDF file.
        """
        if not os.path.exists(pdf_path):
            print(f"Error: File not found at '{pdf_path}'")
            return

        md5, size, file_name = self._get_file_check_data(pdf_path)
        print(f"File: {file_name}, Size: {size} bytes, MD5: {md5}")

        # **Initiate new upload** using the POST /account/articles/{article_id}/files endpoint [1]
        file_info = self._initiate_new_upload(article_id, file_name, md5, size)
        upload_url = file_info["upload_url"]
        file_id = file_info["id"]
        file_info = self._raw_issue_request("GET", upload_url)
        file_info["upload_url"] = upload_url
        with open(pdf_path, "rb") as fin:
            for part in file_info["parts"]:
                self._upload_part(file_info, fin, part)
        print("All parts uploaded.")

        self._complete_upload(article_id, file_id)

