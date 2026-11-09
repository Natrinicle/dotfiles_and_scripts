"""Tests for config module."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mempalace_router.config import ConfigError, load_targets


class ConfigTest(unittest.TestCase):
    def _write_yaml(self, content):
        """Helper: write YAML to a temp file and return Path."""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w") as f:
            f.write(content)
        self.addCleanup(lambda: os.unlink(path))
        return Path(path)

    def test_loads_local_and_company(self):
        """Load a config with one local and one company target."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
  acme:
    kind: company
    company: acme
    url: http://acme.example.com
    token_file: /tmp/acme_token
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        self.assertEqual(targets.local.name, "local")
        self.assertEqual(targets.local.kind, "local")
        self.assertEqual(targets.local.url, "http://127.0.0.1:9999")
        self.assertIsNone(targets.local.palace_path)

        self.assertEqual(targets.by_name["acme"].name, "acme")
        self.assertEqual(targets.by_name["acme"].kind, "company")
        self.assertEqual(targets.by_name["acme"].company, "acme")

        self.assertIn("acme", targets.companies)
        self.assertEqual(targets.get("acme").company, "acme")

    def test_exactly_one_local_required(self):
        """Zero or more than one local target must raise ConfigError."""
        # Test zero local targets
        content = """
targets:
  acme:
    kind: company
    company: acme
    url: http://acme.example.com
    token_file: /tmp/token
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("exactly one", str(ctx.exception).lower())

        # Test two local targets
        content = """
targets:
  local1:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token1
  local2:
    kind: local
    palace_path: ${HOME}/.mempalace
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("exactly one", str(ctx.exception).lower())

    def test_company_requires_company_name_url_token(self):
        """Company targets must have company, url, and token_file."""
        # Missing company field
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
  bad:
    kind: company
    url: http://bad.example.com
    token_file: /tmp/token
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("company", str(ctx.exception).lower())

        # Missing url
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
  bad:
    kind: company
    company: bad
    token_file: /tmp/token
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("url", str(ctx.exception).lower())

        # Missing token_file
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
  bad:
    kind: company
    company: bad
    url: http://bad.example.com
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("token_file", str(ctx.exception).lower())

    def test_tilde_expansion(self):
        """~ and $HOME must expand in token_file and palace_path."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: ~/.config/token
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        expanded = str(targets.local.token_file)
        self.assertNotIn("~", expanded)
        self.assertTrue(expanded.startswith("/"))

        # Test $HOME expansion in palace_path
        content = """
targets:
  local:
    kind: local
    palace_path: $HOME/.mempalace
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        expanded = str(targets.local.palace_path)
        self.assertNotIn("$HOME", expanded)
        self.assertTrue(expanded.startswith("/"))

    def test_unknown_kind_rejected(self):
        """Unknown kind values must raise ConfigError."""
        content = """
targets:
  bad:
    kind: unknown
    url: http://unknown.example.com
    token_file: /tmp/token
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("unknown", str(ctx.exception).lower())

    def test_local_with_palace_path(self):
        """A local target can use palace_path instead of url+token_file."""
        content = """
targets:
  local:
    kind: local
    palace_path: ${HOME}/.mempalace
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        self.assertEqual(targets.local.name, "local")
        self.assertIsNone(targets.local.url)
        self.assertIsNone(targets.local.token_file)
        self.assertIsNotNone(targets.local.palace_path)

    def test_local_requires_url_token_or_palace_path(self):
        """A local target must have (url+token_file) or palace_path."""
        # Missing both url/token_file and palace_path
        content = """
targets:
  local:
    kind: local
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)

        # Only url, no token_file
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)

    def test_hints_default_empty_dict(self):
        """hints defaults to an empty dict."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        self.assertEqual(targets.local.hints, {})

    def test_hints_populated(self):
        """hints can be a dict of lists."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
    hints:
      cwd_prefixes:
        - /home/user
        - /tmp
      keywords:
        - palace
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        self.assertIn("cwd_prefixes", targets.local.hints)
        self.assertEqual(targets.local.hints["cwd_prefixes"], ["/home/user", "/tmp"])
        self.assertEqual(targets.local.hints["keywords"], ["palace"])

    def test_get_raises_keyerror_for_missing_name(self):
        """Targets.get() should raise KeyError for unknown names."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        with self.assertRaises(KeyError):
            targets.get("nonexistent")

    def test_company_rejects_palace_path(self):
        """Company targets must not have palace_path field."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
  bad:
    kind: company
    company: bad
    url: http://bad.example.com
    token_file: /tmp/token
    palace_path: /tmp/palace
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("palace_path", str(ctx.exception).lower())
        self.assertIn("bad", str(ctx.exception).lower())

    def test_local_rejects_company_field(self):
        """Local targets must not have company field."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
    company: acme
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("company", str(ctx.exception).lower())
        self.assertIn("local", str(ctx.exception).lower())

    def test_hints_null_becomes_empty_dict(self):
        """hints: null should be treated as an empty dict."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
    hints: null
"""
        path = self._write_yaml(content)
        targets = load_targets(path)
        self.assertEqual(targets.local.hints, {})

    def test_hints_scalar_rejected(self):
        """hints as a scalar value must raise ConfigError."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
    hints: "scalar"
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("hints", str(ctx.exception).lower())

    def test_hints_with_non_list_values_rejected(self):
        """hints values must all be lists."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
    hints:
      cwd_prefixes: /home/user
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("hints", str(ctx.exception).lower())

    def test_hints_with_non_string_items_rejected(self):
        """hints list items must be strings."""
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: /tmp/token
    hints:
      cwd_prefixes:
        - /home/user
        - 123
"""
        path = self._write_yaml(content)
        with self.assertRaises(ConfigError) as ctx:
            load_targets(path)
        self.assertIn("hints", str(ctx.exception).lower())

    def test_malformed_yaml_raises_configerror(self):
        """Malformed YAML must raise ConfigError (not YAMLError)."""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w") as f:
            f.write("invalid: yaml: content: [")
        self.addCleanup(lambda: os.unlink(path))

        with self.assertRaises(ConfigError) as ctx:
            load_targets(Path(path))
        self.assertIn("yaml", str(ctx.exception).lower())

    def test_missing_file_raises_configerror(self):
        """Missing config file must raise ConfigError (not FileNotFoundError)."""
        with self.assertRaises(ConfigError) as ctx:
            load_targets(Path("/nonexistent/path/targets.yaml"))
        self.assertIn("not found", str(ctx.exception).lower())

    def test_tilde_expansion_equality(self):
        """~ and $HOME must expand to actual home paths."""
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: os.rmdir(tmpdir))

        # Test ~/x form
        content = """
targets:
  local:
    kind: local
    url: http://127.0.0.1:9999
    token_file: ~/test_token
"""
        path = self._write_yaml(content)
        targets = load_targets(path)

        expected = Path.home() / "test_token"
        self.assertEqual(targets.local.token_file, expected)

        # Test $HOME/x form with mocked HOME
        with mock.patch.dict(os.environ, {"HOME": tmpdir}):
            content = """
targets:
  local:
    kind: local
    palace_path: $HOME/palace
"""
            path = self._write_yaml(content)
            targets = load_targets(path)

            expected_palace = Path(tmpdir) / "palace"
            self.assertEqual(targets.local.palace_path, expected_palace)


if __name__ == "__main__":
    unittest.main()
