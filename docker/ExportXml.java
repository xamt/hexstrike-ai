// 为原接口提供无交互 XML 导出入口，使用 Ghidra 12.1.4 的正式导出 API。
// @category HexStrike

import java.io.File;
import java.io.IOException;

import ghidra.app.script.GhidraScript;
import ghidra.app.util.exporter.XmlExporter;

/** 将当前分析程序导出到唯一的脚本路径参数，不更改原 HTTP 接口。 */
public class ExportXml extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] arguments = getScriptArgs();
        if (arguments.length != 1 || arguments[0].isBlank()) {
            throw new IllegalArgumentException("ExportXml.java 需要一个非空输出文件路径");
        }
        if (currentProgram == null) {
            throw new IllegalStateException("没有可导出的已分析程序");
        }

        File output = new File(arguments[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (!parent.isDirectory() && !parent.mkdirs()) {
            throw new IOException("无法创建 XML 输出目录: " + parent);
        }

        XmlExporter exporter = new XmlExporter();
        if (!exporter.export(output, currentProgram, null, monitor)) {
            throw new IOException("Ghidra XML 导出失败: " + exporter.getMessageLog());
        }
        println("XML 分析报告已写入: " + output);
    }
}
