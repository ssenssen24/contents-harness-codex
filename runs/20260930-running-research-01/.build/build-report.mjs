import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {GlobalFonts} from '@napi-rs/canvas';
GlobalFonts.registerFromPath('/Library/Fonts/Pretendard-Regular.otf','Pretendard');
GlobalFonts.registerFromPath('/Library/Fonts/Pretendard-Bold.otf','Pretendard');
const {Presentation,PresentationFile,FileBlob}=await import('@oai/artifact-tool');
const RUN=path.resolve(import.meta.dirname,'..');
const SKILL='/Users/bibi/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const data=JSON.parse(await fs.readFile(RUN+'/research/sources.json','utf8'));
const selected=data.selected_ids.map(id=>data.posts.find(p=>p.id===id));
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const C={bg:'#141713',white:'#F7F8F3',muted:'#C2C8BE',lime:'#E6FF65'};
function text(s,str,x,y,w,h,size=24,color=C.white,bold=false){
 const el=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 el.text=str;el.text.style={typeface:'Pretendard',fontSize:size,color,bold,autoFit:'none'};return el;
}
function slide(label,title){const s=deck.slides.add();s.background.fill=C.bg;
 text(s,label.toUpperCase(),48,30,1140,30,17,C.lime,true);
 text(s,title,48,82,1184,90,46,C.white,true);
 text(s,'RUNMATE / COMPETITOR RESEARCH · 2026.09.30',48,679,1060,24,15,C.muted);
 text(s,String(deck.slides.items.length).padStart(2,'0'),1180,679,52,24,15,C.muted);
 return s;
}
let s=slide('RESEARCH / 01','함께 달리기를 말하는 방식');
text(s,'Nike Running × adidas Running',48,207,1150,68,38,C.lime,true);
text(s,'최근 90일 경쟁사 조사\n확인한 게시물 중 정확한 좋아요 수 기준 6개 분석',48,312,1130,114,30);
text(s,'기간  2026.07.02 08:42 — 09.30 08:42 KST\n방법  Aside 화면·DOM 직접 열람 / 계정 통합 순위\n목적  런메이트의 다음 카드뉴스 주제 선택',48,493,1130,142,24,C.muted);
s.speakerNotes.textFrame.setText('기준 문서: brand.md, content-design.md. '+data.limitations);
s=slide('READ THIS FIRST','이 보고서의 순위에는 한계가 있습니다');
text(s,'전체 인기 Top 6로 해석하지 않습니다.',48,195,1180,60,34,C.lime,true);
text(s,'01  ‘만’ 단위 축약 수치를 정확한 정수로 바꾸지 않았습니다.\n02  축약 표시 게시물은 순위에서 제외하고 출처에 따로 기록했습니다.\n03  선정 목록보다 실제 좋아요가 많은 제외 게시물이 존재합니다.\n04  조회수·도달·광고 집행·참여율·성과 원인은 확인되지 않았습니다.',48,282,1180,250,25);
text(s,data.coverage_summary,48,550,1170,90,21,C.muted);
s.speakerNotes.textFrame.setText(data.limitations+'\n'+JSON.stringify(data.coverage));
s=slide('LIMITATION / EXAMPLES','큰 반응의 게시물도 순위에서 빠졌습니다');
const excluded=['DdlQYW8DK7f','DcYhRAzDOJA'].map(code=>data.posts.find(p=>p.url.includes(code)));
for(const [i,p] of excluded.entries()){
 const y=195+i*205;
 text(s,p.displayed_likes+' 표시',48,y,410,75,50,C.lime,true);
 text(s,'정확한 정수 미확인 → 순위 제외',465,y+4,755,56,30,C.white,true);
 text(s,p.id+' · '+p.account+' · 게시 '+p.published_at.slice(0,10)+' UTC',465,y+68,755,35,21,C.muted);
 text(s,p.url,48,y+126,1180,35,19,C.muted);
}
text(s,'화면의 축약값을 임의 환산하지 않았습니다. 아래 선정작을 전체 인기 순위로 사용하지 마세요.',48,621,1185,44,22,C.muted);
s.speakerNotes.textFrame.setText(excluded.map(p=>p.url+'\n확인 '+p.checked_at+'\n'+p.unknown_reasons.likes).join('\n'));
s=slide('OBSERVED RANKING','확인한 게시물 중 좋아요 순위');
selected.forEach((p,i)=>{
 const y=190+i*67;
 text(s,String(i+1).padStart(2,'0'),48,y,63,47,30,C.lime,true);
 text(s,p.title,131,y,695,41,26,C.white,true);
 text(s,p.account+' · '+p.id,843,y+3,212,33,18,C.muted);
 text(s,p.likes.toLocaleString('en-US'),1080,y,150,42,30,C.lime,true);
});
text(s,'조회 당시 수치 · 정확한 정수와 게시일이 확인된 후보만 비교',48,616,1180,40,20,C.muted);
for(const [i,p] of selected.entries()){
 s=slide('POST '+String(i+1).padStart(2,'0')+' / '+p.id,p.title);
 const blob=new Uint8Array(await fs.readFile(path.join(RUN,p.screenshot)));
 const view=new DataView(blob.buffer,blob.byteOffset,blob.byteLength);
 const ratio=view.getUint32(16)/view.getUint32(20);
 const imageW=Math.min(365,454*ratio),imageH=imageW/ratio;
 s.images.add({blob,contentType:'image/png',alt:p.visual,fit:'contain',position:{left:48+(365-imageW)/2,top:184+(454-imageH)/2,width:imageW,height:imageH}});
 text(s,'관찰 · 핵심 내용',449,185,740,30,18,C.lime,true);
 text(s,p.summary,449,222,766,74,26,C.white,true);
 text(s,'시각적 특징  '+p.visual,449,309,766,87,22,C.muted);
 text(s,'해석  '+p.interpretation,449,413,766,77,22);
 text(s,'활용  '+p.application,449,505,766,82,22);
 text(s,p.account+' / 좋아요 '+p.likes.toLocaleString('en-US')+' / 게시 '+p.published_at.slice(0,10)+' UTC',449,598,766,29,17,C.muted);
 text(s,'확인 '+p.checked_at.slice(0,10)+' UTC · 날짜는 원문 time 속성 기준',449,627,766,25,15,C.muted);
 text(s,p.url,48,651,1184,23,15,C.muted);
 s.speakerNotes.textFrame.setText(p.id+'\n'+p.url+'\n확인 '+p.checked_at+'\n게시 '+p.published_at+'\n관찰 '+p.observation+'\n'+data.limitations);
}
s=slide('INTERPRETATION','경쟁사의 성과보다 전달 방식을 가져옵니다');
text(s,'한 장면 + 한 문장',48,201,1140,54,34,C.lime,true);
text(s,'선수·제품·공간을 중심에 두고 짧은 문구로 읽는 순서를 만듭니다.\n런메이트에서는 평범한 동행 장면과 일상어로 전환할 수 있습니다.',48,272,1130,100,27);
text(s,'브랜드 기준이 사진 스타일의 우선순위',48,425,1140,56,34,C.lime,true);
text(s,'경쟁사의 승리·속도·제품 효능은 런메이트의 약속으로 옮기지 않습니다.\n신규 사진은 brand.md와 content-design.md의 편안한 동행을 따릅니다.',48,497,1140,115,27,C.muted);
s.speakerNotes.textFrame.setText('Codex의 해석·기획 제안. 인과적 성과 분석 아님. 기준 문서 brand.md, content-design.md.\n'+selected.map(p=>p.url).join('\n'));
s=slide('NEXT / SELECT A TOPIC','다음 콘텐츠 주제 후보');
const topics=[['01  추천','함께 달려도, 내 페이스는 그대로','대상: 다른 사람의 속도를 따라가는 것이 부담스러운 사람'],['02','혼자 달리기 심심한 날','대상: 혼자 달리는 것이 심심한 러너'],['03','멀리 가지 않아도, 함께 달릴 수 있어요','대상: 동네에서 가볍게 시작하고 싶은 사람']];
topics.forEach(([n,t,b],i)=>{const y=185+i*143;text(s,n,48,y,180,40,23,C.lime,true);text(s,t,236,y,990,48,33,C.white,true);text(s,b,236,y+60,990,46,23,C.muted);});
text(s,'주제 선택 → plan.md 제시 → 기획 승인 → 신규 사진·HTML → 프리뷰 승인 → Figma',48,627,1185,40,20,C.lime);
s.speakerNotes.textFrame.setText('주제는 경쟁사의 성과에서 증명된 결론이 아닌 brand.md에 근거한 Codex 제안. 사용자 선택과 기획 승인은 별도.');
const candidate=RUN+'/.build/candidate-v003.pptx';
await (await PresentationFile.exportPptx(deck)).save(candidate);
await fs.mkdir(RUN+'/research/v003',{recursive:true});
await finalizePresentation({workspaceDir:RUN,candidatePath:candidate,finalPath:RUN+'/research/v003/research.pptx',pythonExecutable:'/Users/bibi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python',integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:['Pretendard']},verifyArtifactToolImport:true,receiptPath:RUN+'/.build/research-v003.validation.json'});
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(RUN+'/research/v003/research.pptx'));
await fs.mkdir(RUN+'/checks/pptx-render',{recursive:true});
for(const [i,sl] of finalDeck.slides.items.entries()){
 const out=await finalDeck.export({slide:sl,format:'png',scale:1});
 await fs.writeFile(RUN+'/checks/pptx-render/slide-'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await out.arrayBuffer()));
}
console.log(JSON.stringify({slides:deck.slides.items.length,final:RUN+'/research/research.pptx'}));
await fs.copyFile(RUN+'/research/v003/research.pptx',RUN+'/research/research.pptx');
