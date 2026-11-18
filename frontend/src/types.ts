export type Source = { id:string; title:string; law:string; article:string; excerpt:string; status:string };
export type Message = { id:string; role:'user'|'assistant'; content:string; sources?:Source[]; feedback?:'up'|'down' };
export type Conversation = { id:string; title:string; messages:Message[]; saved?:boolean };
