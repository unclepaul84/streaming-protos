
package org.example;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.StringJoiner;

/**
 * Helper class to generate metadata.json for a dataset.
 * Strongly typed: uses Index, Tag, and Data classes.
 */

public class MetadataJsonWriter {
    private List<Index> indexes = new ArrayList<>();
    private List<Tag> tags = new ArrayList<>();
    private Data data = null;
    private String filePath = null;
    private java.io.OutputStream outputStream = null;


    public static class Index {
        public final String file;
        public final String description;
        public final String field;

        public Index(String file, String description, String field) {
            this.file = Objects.requireNonNull(file);
            this.description = Objects.requireNonNull(description);
            this.field = Objects.requireNonNull(field);
        }
    }


    public static class Tag {
        public final String name;
        public final String value;

        public Tag(String name, String value) {
            this.name = Objects.requireNonNull(name);
            this.value = Objects.requireNonNull(value);
        }
    }


    public static class Data {
        public final Integer records;
        // Add more fields as needed

        public Data(Integer records) {
            this.records = records;
        }
    }


    /**
     * Construct a writer that writes to a file path.
     */
    public MetadataJsonWriter(String filePath) {
        this.filePath = filePath;
    }

    /**
     * Construct a writer that writes to an OutputStream.
     */
    public MetadataJsonWriter(java.io.OutputStream outputStream) {
        this.outputStream = outputStream;
    }

    /**
     * Default constructor (no output target set).
     */
    public MetadataJsonWriter() {
        // No-op
    }


    /**
     * Add index definitions.
     * @param indexes List of Index objects
     */
    public void setIndexes(List<Index> indexes) {
        this.indexes = indexes != null ? indexes : new ArrayList<>();
    }


    /**
     * Add tags.
     * @param tags List of Tag objects
     */
    public void setTags(List<Tag> tags) {
        this.tags = tags != null ? tags : new ArrayList<>();
    }


    /**
     * Optionally set the data object (e.g., record count).
     * @param data Data object (nullable)
     */
    public void setData(Data data) {
        this.data = data;
    }


    /**
     * Write the metadata.json file to the configured output (file or stream).
     * If both are null, throws IOException.
     * @throws IOException if writing fails
     */
    public void writeToFile() throws IOException {
        String json = toJsonString();
        if (outputStream != null) {
            outputStream.write(json.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            outputStream.flush();
        } else if (filePath != null) {
            try (FileWriter writer = new FileWriter(filePath)) {
                writer.write(json);
            }
        } else {
            throw new IOException("No output target specified (filePath or OutputStream)");
        }
    }

    /**
     * Write the metadata.json file to a specific file path (overrides constructor target).
     * @param filePath Output file path
     * @throws IOException if writing fails
     */
    public void writeToFile(String filePath) throws IOException {
        String json = toJsonString();
        try (FileWriter writer = new FileWriter(filePath)) {
            writer.write(json);
        }
    }

    private String escape(String s) {
        if (s == null) return "null";
        return '"' + s.replace("\\", "\\\\").replace("\"", "\\\"") + '"';
    }

    private String toJsonString() {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        boolean firstSection = true;
        if (indexes != null && !indexes.isEmpty()) {
            sb.append("  \"indexes\": [\n");
            for (int i = 0; i < indexes.size(); i++) {
                Index idx = indexes.get(i);
                sb.append("    {");
                sb.append("\"file\": ").append(escape(idx.file)).append(", ");
                sb.append("\"description\": ").append(escape(idx.description)).append(", ");
                sb.append("\"field\": ").append(escape(idx.field));
                sb.append("}");
                if (i < indexes.size() - 1) sb.append(",");
                sb.append("\n");
            }
            sb.append("  ]");
            firstSection = false;
        }
        if (tags != null && !tags.isEmpty()) {
            if (!firstSection) sb.append(",\n");
            sb.append("  \"tags\": [\n");
            for (int i = 0; i < tags.size(); i++) {
                Tag tag = tags.get(i);
                sb.append("    {");
                sb.append("\"name\": ").append(escape(tag.name)).append(", ");
                sb.append("\"value\": ").append(escape(tag.value));
                sb.append("}");
                if (i < tags.size() - 1) sb.append(",");
                sb.append("\n");
            }
            sb.append("  ]");
            firstSection = false;
        }
        if (data != null) {
            if (!firstSection) sb.append(",\n");
            sb.append("  \"data\": {");
            boolean firstField = true;
            if (data.records != null) {
                sb.append("\"records\": ").append(data.records);
                firstField = false;
            }
            // Add more fields as needed
            sb.append("}");
        }
        sb.append("\n}");
        return sb.toString();
    }
}
