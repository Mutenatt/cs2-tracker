#!/usr/bin/env node
/**
 * Generate frontend module index with Mermaid dependency graph.
 * Uses TypeScript Compiler API (no new dependencies).
 * Run from frontend/ directory:
 *   node tools/build_index.js                   # print to stdout
 *   node tools/build_index.js PROJECT_INDEX.md  # write to file
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, "..");
const srcDir = path.join(frontendDir, "src");

/**
 * Get bucket name from file path (relative to src/).
 */
function getBucket(relPath) {
  const parts = relPath.split(path.sep);
  if (parts.length === 1) return "root";
  if (parts[0] === "context") return "context";
  if (parts[0] === "hooks") return "hooks";
  if (parts[0] === "lib") return "lib";
  if (parts[0] === "data") return "data";
  if (parts[0] === "components") return "components";
  if (parts[0] === "views") return "views";
  // Special hub files
  if (parts[0] === "api.ts") return "api";
  if (parts[0] === "types.ts") return "types";
  return "root";
}

/**
 * Resolve relative import to actual file.
 */
function resolveImport(importPath, fromDir) {
  const candidates = [
    path.join(fromDir, importPath + ".ts"),
    path.join(fromDir, importPath + ".tsx"),
    path.join(fromDir, importPath, "index.ts"),
    path.join(fromDir, importPath, "index.tsx"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return path.relative(srcDir, candidate).replace(/\\/g, "/");
    }
  }
  return null;
}

/**
 * Extract exports and imports from a TypeScript file.
 */
function extractFileInfo(filePath) {
  const text = fs.readFileSync(filePath, "utf8");
  const lines = text.split("\n").length;
  const sf = ts.createSourceFile(
    filePath,
    text,
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );

  const exports = [];
  const imports = [];

  for (const stmt of sf.statements) {
    // Exports
    const modifiers = ts.getModifiers(stmt);
    const isExport = modifiers?.some((m) => m.kind === ts.SyntaxKind.ExportKeyword);

    if (isExport) {
      if (
        ts.isFunctionDeclaration(stmt) ||
        ts.isClassDeclaration(stmt) ||
        ts.isInterfaceDeclaration(stmt) ||
        ts.isTypeAliasDeclaration(stmt)
      ) {
        if (stmt.name) {
          exports.push(stmt.name.text);
        }
      } else if (ts.isVariableStatement(stmt)) {
        for (const decl of stmt.declarationList.declarations) {
          if (decl.name && ts.isIdentifier(decl.name)) {
            exports.push(decl.name.text);
          }
        }
      } else if (ts.isExportDeclaration(stmt)) {
        if (stmt.exportClause && ts.isNamedExports(stmt.exportClause)) {
          for (const element of stmt.exportClause.elements) {
            exports.push(element.name ? element.name.text : "default");
          }
        }
      }
    } else if (
      ts.isExportAssignment(stmt) ||
      (stmt.kind === ts.SyntaxKind.ExportAssignment &&
        modifiers?.some((m) => m.kind === ts.SyntaxKind.DefaultKeyword))
    ) {
      exports.push("default");
    }

    // Imports (relative only)
    if (ts.isImportDeclaration(stmt) && stmt.moduleSpecifier) {
      const moduleSpec = stmt.moduleSpecifier.text;
      if (moduleSpec.startsWith(".")) {
        const fromDir = path.dirname(filePath);
        const resolved = resolveImport(moduleSpec, fromDir);
        if (resolved) {
          imports.push(resolved);
        }
      }
    }
  }

  return {
    exports: exports.slice(0, 15),
    imports: imports.slice(0, 10),
    lines,
  };
}

/**
 * Walk src/ directory and collect file info.
 */
function buildFrontendIndex() {
  if (!fs.existsSync(srcDir)) {
    console.error(`Error: ${srcDir} does not exist`);
    process.exit(1);
  }

  const fileData = {};
  const bucketFiles = {};
  const bucketEdges = {};

  // Walk all .ts/.tsx files
  function walk(dir, relDir = "") {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name.startsWith(".")) continue;
      const fullPath = path.join(dir, entry.name);
      const relPath = relDir ? path.join(relDir, entry.name) : entry.name;
      if (entry.isDirectory()) {
        walk(fullPath, relPath);
      } else if (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx")) {
        const info = extractFileInfo(fullPath);
        const bucket = getBucket(relPath);

        if (!bucketFiles[bucket]) bucketFiles[bucket] = [];
        if (!fileData[relPath]) fileData[relPath] = info;

        bucketFiles[bucket].push(relPath);

        // Build edges
        for (const imp of info.imports) {
          const dstBucket = getBucket(imp);
          if (dstBucket !== bucket) {
            const key = `${bucket}->${dstBucket}`;
            bucketEdges[key] = (bucketEdges[key] || 0) + 1;
          }
        }
      }
    }
  }

  walk(srcDir);

  const allBuckets = Object.keys(bucketFiles).sort();
  const files = Object.keys(fileData).length;
  const totalLines = Object.values(fileData).reduce((sum, info) => sum + info.lines, 0);

  // Build Mermaid graph
  const mermaidLines = ["graph LR"];
  for (const bucket of allBuckets) {
    const count = bucketFiles[bucket].length;
    mermaidLines.push(`    ${bucket}["${bucket}/\\n${count} files"]`);
  }

  const sortedEdges = Object.entries(bucketEdges)
    .map(([key, count]) => {
      const [src, dst] = key.split("->");
      return [src, dst, count];
    })
    .sort();

  for (const [src, dst, count] of sortedEdges) {
    mermaidLines.push(`    ${src} -->|${count}| ${dst}`);
  }

  // Build output
  const output = [
    "<!-- AUTO-GENERATED by `node tools/build_index.js`. DO NOT EDIT. -->",
    "",
    "# Frontend Index — src/",
    "",
    `${files} files · ${totalLines} lines`,
    "",
    "## Module Graph",
    "",
    "```mermaid",
    ...mermaidLines,
    "```",
    "",
    "## Summary by Module",
    "",
    "| Module | Files | Lines | Description |",
    "|---|---|---|---|",
  ];

  for (const bucket of allBuckets) {
    const files = bucketFiles[bucket];
    const lines = files.reduce((sum, f) => sum + fileData[f].lines, 0);
    let desc = "";
    if (bucket === "api") desc = "HTTP client, all backend routes";
    else if (bucket === "types") desc = "TypeScript types/interfaces (foundation)";
    else if (bucket === "components") desc = "Presentational components";
    else if (bucket === "views") desc = "Page-level components";
    else if (bucket === "context") desc = "React Context state";
    else if (bucket === "hooks") desc = "Custom React hooks";
    else if (bucket === "lib") desc = "Utility functions";
    else if (bucket === "data") desc = "Data constants";

    output.push(`| \`${bucket}/\` | ${files.length} | ${lines} | ${desc} |`);
  }

  // Per-bucket file tables
  for (const bucket of allBuckets) {
    output.push("", `## ${bucket}/`, "", "| File | Lines | Exports | Imports |", "|---|---|---|---|");

    const files = bucketFiles[bucket].sort();
    for (const file of files) {
      const info = fileData[file];
      const exports = info.exports.length > 0 ? info.exports.join(", ") : "—";
      const importsStr = info.imports.length > 0 ? info.imports.slice(0, 2).join(", ") : "—";
      output.push(`| \`${file}\` | ${info.lines} | ${exports} | ${importsStr} |`);
    }
  }

  return output.join("\n");
}

// Main
const result = buildFrontendIndex();
const outputPath = process.argv[2];
if (outputPath) {
  fs.writeFileSync(outputPath, result, "utf8");
  const stats = fs.statSync(outputPath);
  console.log(`Indexed frontend files. Wrote ${outputPath} (${stats.size} bytes).`);
} else {
  console.log(result);
}
