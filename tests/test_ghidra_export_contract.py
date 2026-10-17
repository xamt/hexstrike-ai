"""使用官方方法签名的 Java 替身检查兼容脚本，不启动 Ghidra 或镜像。"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
    "ghidra/framework/model/DomainObject.java": """
package ghidra.framework.model;
public class DomainObject {}
""",
    "ghidra/program/model/address/AddressSetView.java": """
package ghidra.program.model.address;
public interface AddressSetView {}
""",
    "ghidra/util/task/TaskMonitor.java": """
package ghidra.util.task;
public interface TaskMonitor {}
""",
    "ghidra/app/script/GhidraScript.java": """
package ghidra.app.script;
import ghidra.framework.model.DomainObject;
import ghidra.util.task.TaskMonitor;
public abstract class GhidraScript {
    public String[] args = new String[0];
    public DomainObject currentProgram = new DomainObject();
    public TaskMonitor monitor = null;
    public String[] getScriptArgs() { return args; }
    public void println(String value) {}
    public abstract void run() throws Exception;
}
""",
    "ghidra/app/util/exporter/XmlExporter.java": """
package ghidra.app.util.exporter;
import java.io.File;
import ghidra.framework.model.DomainObject;
import ghidra.program.model.address.AddressSetView;
import ghidra.util.task.TaskMonitor;
public class XmlExporter {
    public static boolean result = true;
    public boolean export(File file, DomainObject program, AddressSetView set, TaskMonitor monitor)
            throws Exception {
        if (program == null || set != null) throw new AssertionError("wrong export contract");
        if (result) java.nio.file.Files.writeString(file.toPath(), "<PROGRAM/>");
        return result;
    }
    public Object getMessageLog() { return "stub export failed"; }
}
""",
    "ExportHarness.java": """
public class ExportHarness {
    public static void main(String[] args) throws Exception {
        ExportXml script = new ExportXml();
        script.args = args.length > 1 ? new String[] {args[1]} : new String[0];
        if (args[0].equals("no-program")) script.currentProgram = null;
        if (args[0].equals("failed-export")) ghidra.app.util.exporter.XmlExporter.result = false;
        try {
            script.run();
            if (!args[0].equals("success")) throw new AssertionError("failure was hidden");
        } catch (java.io.IOException | IllegalArgumentException | IllegalStateException expected) {
            if (args[0].equals("success")) throw expected;
        }
    }
}
""",
}


class GhidraExportContractTests(unittest.TestCase):
    def test_script_preserves_existing_name_and_uses_official_exporter(self):
        source = (ROOT / "docker/compat/ExportXml.java").read_text()
        self.assertIn("public class ExportXml extends GhidraScript", source)
        self.assertIn("new XmlExporter()", source)
        self.assertIn("export(output, currentProgram, null, monitor)", source)
        self.assertNotIn("askFile(", source)

    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "本地没有 Java 编译环境，仅运行源码契约检查")
    def test_compile_and_execute_with_api_stubs(self):
        with tempfile.TemporaryDirectory(prefix="ghidra-export-contract-") as directory:
            root = Path(directory)
            sources = dict(STUBS)
            sources["ExportXml.java"] = (ROOT / "docker/compat/ExportXml.java").read_text()
            for name, content in sources.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", str(root),
                            *[str(root / name) for name in sources]], check=True, capture_output=True)
            for mode in ("success", "no-args", "no-program", "failed-export"):
                with self.subTest(mode=mode):
                    command = ["java", "-cp", str(root), "ExportHarness", mode]
                    output = root / mode / "with space.xml"
                    if mode != "no-args":
                        command.append(str(output))
                    subprocess.run(command, check=True, capture_output=True)
                    if mode == "success":
                        self.assertEqual(output.read_text(), "<PROGRAM/>")


if __name__ == "__main__":
    unittest.main()
