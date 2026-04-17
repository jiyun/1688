import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.exceptions import (
    ScraperError, ParseError, DownloadError,
    DatabaseError, ConfigError, BrowserError
)


class TestExceptionHierarchy(unittest.TestCase):

    def test_scraper_error_is_base(self):
        with self.assertRaises(ScraperError):
            raise ScraperError("base error")

    def test_parse_error_inherits_scraper_error(self):
        with self.assertRaises(ScraperError):
            raise ParseError("parse failed")

    def test_download_error_inherits_scraper_error(self):
        with self.assertRaises(ScraperError):
            raise DownloadError("download failed")

    def test_database_error_inherits_scraper_error(self):
        with self.assertRaises(ScraperError):
            raise DatabaseError("db error")

    def test_config_error_inherits_scraper_error(self):
        with self.assertRaises(ScraperError):
            raise ConfigError("config error")

    def test_browser_error_inherits_scraper_error(self):
        with self.assertRaises(ScraperError):
            raise BrowserError("browser error")

    def test_parse_error_attributes(self):
        err = ParseError("bad html", url="https://example.com")
        self.assertEqual(err.url, "https://example.com")
        self.assertIn("bad html", str(err))

    def test_download_error_attributes(self):
        err = DownloadError("timeout", url="https://example.com", retryable=True)
        self.assertEqual(err.url, "https://example.com")
        self.assertTrue(err.retryable)

    def test_catch_specific_not_base(self):
        try:
            raise ParseError("specific")
        except DownloadError:
            self.fail("ParseError should not be caught as DownloadError")
        except ScraperError:
            pass


class TestConfigManager(unittest.TestCase):

    def setUp(self):
        from utils.config_manager import ConfigManager
        ConfigManager._instance = None
        self.cm = ConfigManager()

    def test_singleton(self):
        from utils.config_manager import ConfigManager, get_config_manager
        cm2 = get_config_manager()
        self.assertIs(self.cm, cm2)

    def test_get_json_config_missing(self):
        result = self.cm.get_json_config("nonexistent_config_xyz")
        self.assertEqual(result, {})

    def test_save_and_get_json_config(self):
        test_data = {"key": "value", "nested": {"a": 1}}
        self.cm.save_json_config("_test_config", test_data)
        result = self.cm.get_json_config("_test_config")
        self.assertEqual(result["key"], "value")
        self.assertEqual(result["nested"]["a"], 1)
        self.cm.invalidate("_test_config")

    def test_invalidate_specific(self):
        self.cm.save_json_config("_test_a", {"x": 1})
        self.cm.save_json_config("_test_b", {"y": 2})
        self.cm.invalidate("_test_a")
        self.assertNotIn("_test_a", self.cm._json_configs)
        self.assertIn("_test_b", self.cm._json_configs)
        import os
        for name in ["_test_a", "_test_b"]:
            path = self.cm.config_dir / f"{name}.json"
            if path.exists():
                os.remove(path)

    def test_invalidate_all(self):
        self.cm.save_json_config("_test_c", {"z": 3})
        self.cm.invalidate()
        self.assertNotIn("_test_c", self.cm._json_configs)
        import os
        path = self.cm.config_dir / "_test_c.json"
        if path.exists():
            os.remove(path)

    def test_project_root(self):
        self.assertTrue(self.cm.project_root.exists())

    def test_config_dir(self):
        self.assertTrue(str(self.cm.config_dir).endswith("config"))


class TestLogger(unittest.TestCase):

    def test_get_logger(self):
        from utils.logger import get_logger
        log = get_logger("TestModule")
        self.assertEqual(log.name, "TestModule")

    def test_logger_singleton_per_name(self):
        from utils.logger import get_logger
        log1 = get_logger("SameName")
        log2 = get_logger("SameName")
        self.assertIs(log1, log2)

    def test_bind_creates_new_instance(self):
        from utils.logger import get_logger
        log1 = get_logger("BindTest")
        log2 = log1.bind(product_id="123")
        self.assertIsNot(log1, log2)
        self.assertEqual(log2._context, {"product_id": "123"})

    def test_bind_preserves_context(self):
        from utils.logger import get_logger
        log1 = get_logger("ChainTest").bind(a=1)
        log2 = log1.bind(b=2)
        self.assertEqual(log2._context, {"a": 1, "b": 2})

    def test_format_message_with_context(self):
        from utils.logger import get_logger
        log = get_logger("FmtTest").bind(x="val")
        msg = log._format_message("INFO", "hello")
        self.assertIn("[INFO]", msg)
        self.assertIn("[FmtTest]", msg)
        self.assertIn("[x=val]", msg)
        self.assertIn("hello", msg)

    def test_format_message_without_context(self):
        from utils.logger import get_logger
        log = get_logger("App")
        msg = log._format_message("WARNING", "test")
        self.assertIn("[WARNING]", msg)
        self.assertNotIn("[App]", msg)
        self.assertIn("test", msg)


class TestParseImportLine(unittest.TestCase):

    def test_valid_url_with_dsid(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("https://detail.1688.com/offer/123456789.html 99999")
        self.assertTrue(result['valid'])
        self.assertEqual(result['product_id'], '123456789')
        self.assertEqual(result['dsid'], '99999')

    def test_valid_url_with_price(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("https://detail.1688.com/offer/987654321.html 【¥25.00】 88888")
        self.assertTrue(result['valid'])
        self.assertEqual(result['product_id'], '987654321')
        self.assertEqual(result['target_price'], 25.0)
        self.assertEqual(result['dsid'], '88888')

    def test_empty_line(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("")
        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], '空行')

    def test_no_url(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("just some text without url")
        self.assertFalse(result['valid'])
        self.assertIn('URL', result['error'])

    def test_url_no_product_id(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("https://example.com/page")
        self.assertFalse(result['valid'])
        self.assertIn('商品ID', result['error'])

    def test_price_with_yuan_sign(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("https://detail.1688.com/offer/111111111.html 价格99.0 77777")
        self.assertTrue(result['valid'])
        self.assertEqual(result['target_price'], 99.0)

    def test_dsid_must_be_digits(self):
        from gui.dialog import parse_import_line
        result = parse_import_line("https://detail.1688.com/offer/222222222.html ABCxyz")
        self.assertTrue(result['valid'])
        self.assertIsNone(result['dsid'])


class TestParserFactory(unittest.TestCase):

    def test_detect_alibaba_platform(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><img src="https://img.alicdn.com/test.jpg"></html>'
        self.assertEqual(ParserFactory.detect_platform(html), 'alibaba')

    def test_detect_jd_platform(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><img src="https://img14.360buyimg.com/test.jpg"></html>'
        self.assertEqual(ParserFactory.detect_platform(html), 'jd')

    def test_detect_unknown_platform(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><body>plain content</body></html>'
        self.assertEqual(ParserFactory.detect_platform(html), 'unknown')

    def test_create_alibaba_parser(self):
        from utils.parsers.factory import ParserFactory
        from utils.parsers.alibaba_parser import AlibabaParser
        html = '<html><img src="https://img.alicdn.com/test.jpg"></html>'
        parser = ParserFactory.create_parser(html)
        self.assertIsInstance(parser, AlibabaParser)

    def test_create_jd_parser(self):
        from utils.parsers.factory import ParserFactory
        from utils.parsers.jd_parser import JDParser
        html = '<html><img src="https://img14.360buyimg.com/test.jpg"></html>'
        parser = ParserFactory.create_parser(html)
        self.assertIsInstance(parser, JDParser)

    def test_create_parser_unknown_returns_none(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><body>nothing</body></html>'
        parser = ParserFactory.create_parser(html)
        self.assertIsNone(parser)

    def test_get_supported_platforms(self):
        from utils.parsers.factory import ParserFactory
        platforms = ParserFactory.get_supported_platforms()
        self.assertIn('alibaba', platforms)
        self.assertIn('jd', platforms)

    def test_detect_jd_with_vod(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><video src="https://vod.300hu.com/vod.mp4"></html>'
        self.assertEqual(ParserFactory.detect_platform(html), 'jd')

    def test_detect_alibaba_with_O1CN01(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><img src="https://cbu01.alicdn.com/O1CN01abc123/test.jpg"></html>'
        self.assertEqual(ParserFactory.detect_platform(html), 'alibaba')

    def test_mixed_signals_jd_wins(self):
        from utils.parsers.factory import ParserFactory
        html = '<html><img src="https://img14.360buyimg.com/a.jpg"><img src="https://img30.360buyimg.com/b.jpg"><p>alicdn.com</p></html>'
        self.assertEqual(ParserFactory.detect_platform(html), 'jd')


class TestBaseParser(unittest.TestCase):

    def test_detect_platform_static_alibaba(self):
        from utils.parsers.base_parser import BaseParser
        html = '<html><img src="https://img.alicdn.com/test.jpg"></html>'
        self.assertEqual(BaseParser.detect_platform(html), 'alibaba')

    def test_detect_platform_static_jd(self):
        from utils.parsers.base_parser import BaseParser
        html = '<html><img src="https://img14.360buyimg.com/test.jpg"></html>'
        self.assertEqual(BaseParser.detect_platform(html), 'jd')

    def test_detect_platform_static_unknown(self):
        from utils.parsers.base_parser import BaseParser
        html = '<html><body>plain</body></html>'
        self.assertEqual(BaseParser.detect_platform(html), 'unknown')

    def test_cannot_instantiate_abstract(self):
        from utils.parsers.base_parser import BaseParser
        with self.assertRaises(TypeError):
            BaseParser('<html></html>')


class TestAlibabaParserExtractImageId(unittest.TestCase):

    def test_extract_image_id_from_alicdn(self):
        from utils.parsers.alibaba_parser import AlibabaParser
        html = '<html><body></body></html>'
        parser = AlibabaParser(html)
        result = parser._extract_image_id('https://cbu01.alicdn.com/img/ibank/O1CN01abc123_1234567.jpg')
        self.assertIsNotNone(result)

    def test_extract_image_id_from_plain_url(self):
        from utils.parsers.alibaba_parser import AlibabaParser
        html = '<html><body></body></html>'
        parser = AlibabaParser(html)
        result = parser._extract_image_id('https://example.com/no_id_here.jpg')
        self.assertIsNone(result)

    def test_normalize_url_removes_webp_suffix(self):
        from utils.parsers.alibaba_parser import AlibabaParser
        html = '<html><body></body></html>'
        parser = AlibabaParser(html)
        result = parser._normalize_url('https://example.com/img.jpg_.webp')
        self.assertFalse(result.endswith('_.webp'))

    def test_normalize_url_removes_jpg_sum(self):
        from utils.parsers.alibaba_parser import AlibabaParser
        html = '<html><body></body></html>'
        parser = AlibabaParser(html)
        result = parser._normalize_url('https://example.com/img.jpg_sum')
        self.assertNotIn('.jpg_sum', result)

    def test_normalize_url_empty(self):
        from utils.parsers.alibaba_parser import AlibabaParser
        html = '<html><body></body></html>'
        parser = AlibabaParser(html)
        result = parser._normalize_url('')
        self.assertEqual(result, '')


if __name__ == '__main__':
    unittest.main()
