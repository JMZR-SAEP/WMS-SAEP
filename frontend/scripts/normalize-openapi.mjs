import { readFileSync, writeFileSync } from "node:fs";

const schemaPath = new URL("../openapi/schema.json", import.meta.url);
const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const components = schema.components?.schemas;

if (!components) {
  throw new Error("Schema export sem components.schemas.");
}

if (!components.BeneficiaryLookupOutput) {
  components.BeneficiaryLookupOutput = {
    type: "object",
    properties: {
      id: {
        type: "integer",
        readOnly: true,
      },
      matricula_funcional: {
        type: "string",
        readOnly: true,
      },
      nome_completo: {
        type: "string",
        readOnly: true,
      },
      setor: {
        allOf: [
          {
            $ref: "#/components/schemas/AuthSetorOutput",
          },
        ],
        readOnly: true,
        nullable: true,
      },
    },
    required: ["id", "matricula_funcional", "nome_completo", "setor"],
  };
}

writeFileSync(schemaPath, `${JSON.stringify(schema, null, 2)}\n`);
