import {describe,it,expect,vi,afterEach} from 'vitest';
import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import App from './App';

afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();localStorage.clear();window.location.hash=''});

describe('Legal assistant frontend',()=>{
 it('renders the landing page and navigates to chat',()=>{
  render(<App/>);
  expect(screen.getByRole('heading',{name:/مساعدك القانوني/})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:/ابدأ الآن/}));
  expect(screen.getByRole('heading',{name:'قانوني'})).toBeInTheDocument();
 });
 it('does not send an empty message',()=>{
  render(<App/>);
  fireEvent.click(screen.getByRole('button',{name:/ابدأ الآن/}));
  expect(screen.getByRole('button',{name:'إرسال السؤال'})).toBeDisabled();
 });
 it('sends a question to the API and renders its grounded response',async()=>{
  const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({
   conversation_id:'server-conversation-1',status:'answered',answer:'## الإجابة المستندة إلى المصدر\n\n**[S1]**',
   sources:[{source_id:'S1',law_name:'قانون تجريبي',categories:'تشريع',unit_label:'المادة 1',unit_type:'article',article_number:'1',excerpt:'نص المصدر',expanded:false}]
  })});
  vi.stubGlobal('fetch',fetchMock);
  render(<App/>);
  fireEvent.click(screen.getByRole('button',{name:/ابدأ الآن/}));
  fireEvent.change(screen.getByLabelText('اكتب سؤالك القانوني'),{target:{value:'ما هي شروط عقد الإيجار؟'}});
  fireEvent.click(screen.getByRole('button',{name:'إرسال السؤال'}));
  expect(screen.getAllByText('ما هي شروط عقد الإيجار؟').length).toBeGreaterThan(0);
  await waitFor(()=>expect(screen.getByRole('heading',{name:'الإجابة المستندة إلى المصدر'})).toBeInTheDocument());
  expect(screen.getByText('[S1]')).toBeInTheDocument();
  expect(screen.getByText('قانون تجريبي')).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/chat',expect.objectContaining({method:'POST'}));
 });
});
