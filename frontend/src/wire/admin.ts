export interface MissingCapability {
  name: string;
  code: string;
}
/** An explicit unavailable capability that names what is missing (IA_SPEC.md 4.9). */
export interface AdminBody {
  capability: string;
  missing: MissingCapability[];
}
