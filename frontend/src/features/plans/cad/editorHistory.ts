export interface HistoryEntry<T> {
  before: T;
  after: T;
}

export class EditorHistory<T> {
  private undoEntries: HistoryEntry<T>[] = [];
  private redoEntries: HistoryEntry<T>[] = [];

  constructor(private readonly limit = 40) {}

  get canUndo(): boolean {
    return this.undoEntries.length > 0;
  }

  get canRedo(): boolean {
    return this.redoEntries.length > 0;
  }

  record(entry: HistoryEntry<T>): void {
    this.undoEntries.push(entry);
    if (this.undoEntries.length > this.limit) this.undoEntries.shift();
    this.redoEntries = [];
  }

  undo(): HistoryEntry<T> | null {
    const entry = this.undoEntries.pop() ?? null;
    if (entry) this.redoEntries.push(entry);
    return entry;
  }

  redo(): HistoryEntry<T> | null {
    const entry = this.redoEntries.pop() ?? null;
    if (entry) this.undoEntries.push(entry);
    return entry;
  }

  clear(): void {
    this.undoEntries = [];
    this.redoEntries = [];
  }
}
