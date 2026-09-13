export type LegacyProjectType = "youtube" | "premium";
export type SemanticProjectType = "content" | "formation";
export type EditorialProjectType = LegacyProjectType | SemanticProjectType;

export function normalizeProjectType(
  projectType: EditorialProjectType,
): SemanticProjectType {
  if (projectType === "youtube") return "content";
  if (projectType === "premium") return "formation";
  return projectType;
}

export function isContentFlow(projectType: EditorialProjectType): boolean {
  return normalizeProjectType(projectType) === "content";
}

export function isFormationFlow(projectType: EditorialProjectType): boolean {
  return normalizeProjectType(projectType) === "formation";
}