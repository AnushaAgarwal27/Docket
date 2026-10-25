// Shared HTTP response contracts. IDs are opaque SQLite document identifiers.
export type TableNames = 'profiles'|'paystubs'|'transactions'|'flags'|'cases'|'calls'|'sources'|'activity'|'hearings'|'files';
export type Id<T extends TableNames> = string & { readonly __table: T };
type Base<T extends TableNames> = { _id: Id<T>; _creationTime: number };
export type Profile = Base<'profiles'> & { name:string; visa:string; arrivalDate:string; school:string; homeCountry:string; homeCurrency:string; workAuth:string; phoneMasked:string; filed8843Years?:number[]; employer?:string; simulated?:boolean; preferredLanguage?:string };
export type Paystub = Base<'paystubs'> & { profileId:Id<'profiles'>; periodStart:string; periodEnd:string; employer:string; grossCents:number; hoursByWeek:number[]; ssCents:number; medicareCents:number; netCents:number; sourceFile:string; warnings?:string[]; depositId?:Id<'transactions'> };
export type Transaction = Base<'transactions'> & { profileId:Id<'profiles'>; kind:string; amountCents:number; date:string; counterparty:string; memo:string; nessieId:string };
export type Flag = Base<'flags'> & { profileId:Id<'profiles'>; ruleId:string; amountCents:number; explanation:string; quote:string; sourceId:Id<'sources'>; status:string; sourceTitle:string|null; sourceUrl:string|null; sourceFetchedAt:string|null; sourceHash:string|null; paystubIds?:Id<'paystubs'>[] };
export type Call = Base<'calls'> & { caseId:Id<'cases'>; answeredBy:string; at:string; summary:string; promisedBy?:string; referenceNo?:string };
export type Case = Base<'cases'> & { flagId:Id<'flags'>; profileId?:Id<'profiles'>; state:string; amountCents:number; nextFollowUp:string; outcome?:string; draft?:string; calls:Call[]; callRequestedAt?:string|null; callRequestId?:string|null; callError?:string|null; callAttempts?:number; payrollScript?:'cooperate'|'stall_once'|'refuse_once'; writtenRequest?:string; writtenRequestAt?:string };
export type Activity = Base<'activity'> & { agent:string; action:string; detail:string; at:string; sourceId?:Id<'sources'>; inputIds?:string[]; outputIds?:string[]; kind?:string; sender?:string; receiver?:string; summary?:string };
export type Snapshot = { profile:Profile; flags:Flag[]; cases:Case[]; paystubs:Paystub[]; transactions:Transaction[] };
export type Timeline = { events:{date:string; title:string; detail:string; tone:'done'|'warn'|'info'|'next'; upcoming:boolean}[]; nextSeason:{date:string;title:string;detail:string}; calendarYear:number; lastExemptYear:number };
export type Patterns = { employers:{employer:string;students:number;flagged:number;withheldCents:number;simulated:number;pattern:boolean}[]; minForPattern:number;anySimulated:boolean };
export type FileRecord = Base<'files'> & { url:string; filename:string; kind:string; periodStart?:string|null };
export type Receipt = { paystubs:FileRecord[]; letters:FileRecord[]; forms:FileRecord[] };
