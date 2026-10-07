export function fullName(item: { last_name: string; first_name: string; middle_name: string | null }) {
  return [item.last_name, item.first_name, item.middle_name].filter(Boolean).join(" ");
}

export function childCompactName(item: { last_name: string; first_name: string; middle_name: string | null }) {
  const initial = item.middle_name?.trim().slice(0, 1);
  return `${item.last_name} ${item.first_name}${initial ? ` ${initial}.` : ""}`;
}

export function parentChildContext(
  parent: { last_name: string; first_name: string; middle_name: string | null },
  relation: string,
  child: { last_name: string; first_name: string; middle_name: string | null },
) {
  return `${fullName(parent)} · связь: ${relation.toLocaleLowerCase("ru")} · ребёнок: ${fullName(child)}`;
}
