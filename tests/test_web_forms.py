import importlib.util
import io
import unittest
from email.message import Message
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "yanshen_web_forms", Path(__file__).parents[1] / "gongkao" / "web" / "forms.py"
)
_forms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_forms)
parse_multipart_form = _forms.parse_multipart_form


def headers(content_type, length):
    message = Message()
    message["Content-Type"] = content_type
    message["Content-Length"] = str(length)
    return message


class MultipartFormTest(unittest.TestCase):
    def test_parse_text_and_binary_uploads(self):
        boundary = "YanShenBoundary"
        file_body = b"a,b\r\n1,\x00\xff2\r\n"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="title"\r\n\r\n'.encode("ascii")
            + "中文标题".encode("utf-8")
            + f"\r\n--{boundary}\r\n".encode("ascii")
            + ('Content-Disposition: form-data; name="question_file"; filename="'.encode("ascii"))
            + "题目.csv".encode("utf-8")
            + '"\r\nContent-Type: text/csv\r\n\r\n'.encode("ascii")
            + file_body
            + f"\r\n--{boundary}--\r\n".encode("ascii")
        )
        stream = io.BytesIO(body)
        form = parse_multipart_form(stream, headers(f"multipart/form-data; boundary={boundary}", len(body)))

        self.assertIn("title", form)
        self.assertEqual(form["title"], "中文标题")
        self.assertIn("question_file", form)
        upload = form["question_file"]
        self.assertEqual(upload.filename, "题目.csv")
        self.assertEqual(upload.file.read(), file_body)

    def test_missing_or_non_multipart_body_is_empty(self):
        self.assertEqual(parse_multipart_form(io.BytesIO(b""), headers("application/x-www-form-urlencoded", 0)).get_list("x"), [])
        self.assertEqual(parse_multipart_form(io.BytesIO(b""), headers("", 0)).get_list("x"), [])


if __name__ == "__main__":
    unittest.main()
