'use strict';
const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
const paths = {
  arrow: 'm5 12 14 0m-6-6 6 6-6 6',
  back: 'M19 12H5m6-6-6 6 6 6',
  pin: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
  calendar: 'M4 5h16v16H4ZM8 3v4m8-4v4M4 10h16',
  people:
    'M16 21v-3a4 4 0 0 0-8 0v3M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8m8 17v-3a4 4 0 0 0-3-4M4 21v-3a4 4 0 0 1 3-4',
  parents:
    'M4 20v-4a4 4 0 0 1 8 0v4m0 0v-4a4 4 0 0 1 8 0v4M8 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6m8 0a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
  family:
    'M3 21v-5a4 4 0 0 1 7-2m11 7v-5a4 4 0 0 0-7-2m-2 7v-3m-4 3v-3a4 4 0 0 1 8 0v3M7 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6m10 0a3 3 0 1 0 0 6 3 3 0 0 0 0-6m-5 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4',
  kids: 'M4 21v-5a4 4 0 0 1 8 0v5m0 0v-4a4 4 0 0 1 8 0v4M8 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6m8 1a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
  plane: 'm2 13 8 1 5 7 2-1-3-7 6-4c3-2 1-4-2-2l-6 4-7-3-2 2 6 4-7-1Z',
  bed: 'M3 18V8m18 10V9H3m0 5h18M7 9V6h5v3m1 0V6h5v3',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8m0-6v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2',
  temple: 'm3 10 9-7 9 7M5 10h14v10H5Zm4 0v10m6-10v10M3 21h18',
  bag: 'M5 7h14l1 14H4Zm3 0V5a4 4 0 0 1 8 0v2',
  coffee: 'M4 8h13v7a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5Zm13 1h2a3 3 0 0 1 0 6h-2M7 3v2m5-2v2',
  food: 'M5 3v6a3 3 0 0 0 6 0V3M8 3v18M19 3v18m0-18c-5 3-5 9 0 9',
  lantern: 'M8 4h8m-9 4h10a5 5 0 0 1 0 10H7A5 5 0 0 1 7 8Zm5 10v4m0-18v4M9 8v10m6-10v10',
  spark: 'm12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z',
  waves: 'M2 8q3-4 6 0t6 0 6 0m-18 5q3-4 6 0t6 0 6 0m-18 5q3-4 6 0t6 0 6 0',
  museum: 'm2 8 10-6 10 6ZM5 10v9m7-9v9m7-9v9M2 22h20',
  walk: 'm14 5 1 0m-1 4-3 5 4 3 1 5m-5-8-3 8m3-13-4 4m7-4 3 4 3 1',
  check: 'm4 12 5 5L20 6',
  close: 'm6 6 12 12M18 6 6 18',
  map: 'm3 5 6-3 6 3 6-3v17l-6 3-6-3-6 3Zm6-3v17m6-14v17',
  download: 'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
  car: 'm4 9 2-5h12l2 5m-17 0h18v10H3Zm3 10v2m12-2v2M6 13h2m8 0h2',
  info: 'M12 11v6m0-11v1M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  clock: 'M12 6v6l4 2M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  heart: 'M12 21S1 14 2 7c1-6 8-6 10-1 2-5 9-5 10 1 1 7-10 14-10 14Z',
};
function icon(name, size = 20) {
  return `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.spark}"/></svg>`;
}
let state = null,
  stage = 'landing',
  formStep = 0,
  selectedDay = 1,
  view = 'day',
  selectedStop = null;
let map,
  mapGroup,
  markers = [],
  requestVersion = 0;
function makeState(i) {
  const preset = CASES[i];
  return {
    caseId: preset.id,
    caseIndex: i,
    adults: preset.adults,
    children: [...preset.children],
    seniors: structuredClone(preset.seniors),
    start: '2026-12-04',
    nights: preset.nights,
    must: preset.must,
    musts: [preset.must],
    avoid_conditions: [],
    korean_need: preset.food,
    local_food: 'mixed',
    avoid_ingredients: [],
    avoid_other: [],
    venues: ['restaurant'],
    profiles: [],
    profileMode: 'not-requested',
    fixes: new Set(),
  };
}
const total = () => state.adults + state.children.length;
function dateAt(day = 0) {
  const date = new Date(state.start + 'T12:00:00');
  date.setDate(date.getDate() + day);
  return date;
}
function dateLabel(day = 0, weekday = false) {
  return dateAt(day).toLocaleDateString('ko-KR', {
    month: 'numeric',
    day: 'numeric',
    ...(weekday ? { weekday: 'short' } : {}),
  });
}
function duration() {
  return `${state.nights}박 ${state.nights + 1}일`;
}
function peopleLabel() {
  return `성인 ${state.adults}명${state.children.length ? ` · 어린이 ${state.children.length}명` : ''}`;
}
function toast(text) {
  const el = $('toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 3200);
}
function focusHeading() {
  const h = $('app').querySelector('h1,h2');
  if (h) {
    h.tabIndex = -1;
    h.focus({ preventScroll: true });
  }
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function disposeMap() {
  if (map) {
    map.remove();
    map = null;
  }
  markers = [];
}
function landing() {
  window.closeWorkspace?.();
  disposeMap();
  stage = 'landing';
  $('app').innerHTML =
    `<section class="landing-hero"><div class="hero-copy"><div class="eyebrow">A TRIP AT YOUR FAMILY'S PACE</div><h1>어디로 갈까, 보다<br><em>누구와 갈까</em>부터.</h1><p>보고 싶은 마음은 그대로.<br>함께 가는 사람의 걸음에 맞춰 만드는 여행.</p><div class="hero-proof"><span>${icon('walk', 16)} 부모님 속도로 다시 재고</span><span>${icon('heart', 16)} 원하는 경험은 지켜요</span></div></div><div class="hero-photo"><img src="assets/hoi-an.jpg" alt="등불과 배가 어우러진 호이안 강변의 저녁"><div class="photo-location">${icon('pin', 16)} Vietnam, Hoi An <span>한 걸음 느리게 만나는 풍경</span></div><div class="photo-tag">우리 가족의 다음 여행<br><strong>다낭 · 호이안</strong></div></div></section>
    <section class="role-intro"><div><span class="small-label">TWO WAYS TO PLAN</span><h2>같은 여행, 서로 다른 시선.</h2><p>우리 가족에게 맞는 여행을 고르거나, 기획자로 일정을 직접 다듬어보세요.</p></div><button class="secondary" id="open-workspace">MD 작업실 둘러보기 ↗</button></section><section class="start-strip"><div><span class="small-label">OUR NEXT TRIP</span><h2>몇 박 며칠, 누구와 떠나세요?</h2></div><div class="strip-item">${icon('pin')}<div><small>여행지</small><strong>다낭 · 호이안</strong></div></div><div class="strip-item">${icon('calendar')}<div><small>여행 기간</small><strong>2박 3일 ~ 5박 6일</strong></div></div><button class="primary" data-start="0">우리 여행 만들기 ${icon('arrow')}</button></section>
    <section class="case-section"><div class="section-top"><div><div class="eyebrow">THREE DIFFERENT FAMILIES</div><h2>같은 여행지, 다른 가족 이야기.</h2></div><p>사례를 고르면 날짜와 인원을 미리 채워드려요.<br>우리 가족에 맞게 바꿔도 좋아요.</p></div><div class="case-grid">${CASES.map((p, i) => `<button class="case-card ${p.color}" data-start="${i}"><div class="case-art"><span class="case-index">0${i + 1}</span>${icon(p.icon, 72)}<span class="case-label">${p.tag}</span></div><div class="case-body"><span class="tiny-label">${p.nights}박 ${p.nights + 1}일 · ${p.adults + p.children.length}명</span><h3>${p.name}</h3><p>${p.desc}</p><div class="case-note">${p.note}</div><span class="case-go">이 가족의 여행 준비하기 ${icon('arrow', 17)}</span></div></button>`).join('')}</div></section>
    <section class="why-strip"><span class="why-number">15<span>분</span></span><div><h3>지도 속 15분과 부모님의 15분은 다르니까.</h3><p>이동 시간에 숨은 관광지 내부의 걸음까지. 장소를 빼기 전에 코스와 휴식을 먼저 조절해요.</p></div>${icon('walk', 48)}</section>`;
}
function start(i) {
  window.closeWorkspace?.();
  state = makeState(i);
  formStep = 0;
  stage = 'form';
  renderForm();
  focusHeading();
}
function countControl(key, value, min, max) {
  return `<div class="counter"><button type="button" data-count="${key}" data-delta="-1" aria-label="${key === 'adults' ? '성인' : key === 'children' ? '어린이' : '부모님·고령 동행자'} 줄이기" ${value <= min ? 'disabled' : ''}>−</button><output>${value}</output><button type="button" data-count="${key}" data-delta="1" aria-label="${key === 'adults' ? '성인' : key === 'children' ? '어린이' : '부모님·고령 동행자'} 늘리기" ${value >= max ? 'disabled' : ''}>+</button></div>`;
}
function selectOptions(items, current) {
  return Object.entries(items)
    .map(
      ([key, label]) =>
        `<option value="${key}" ${key === current ? 'selected' : ''}>${label}</option>`,
    )
    .join('');
}
function renderForm() {
  disposeMap();
  $('app').innerHTML =
    `<div class="form-page"><div class="form-intro"><button class="text-link" id="back-home">${icon('back', 16)} 가족 이야기로</button><div class="eyebrow">LET'S MAKE YOUR TRIP</div><h1>${formStep === 0 ? '함께 떠나는 사람부터<br>알려주세요.' : '우리 가족의 속도를<br>조금 더 알아볼게요.'}</h1><p>${formStep === 0 ? '날짜와 인원을 고르면 여행의 윤곽이 잡혀요.' : '나이는 출발점일 뿐. 평소 걷는 모습과 식사 취향도 함께 생각해요.'}</p><ol class="form-progress"><li class="${formStep === 0 ? 'active' : 'done'}"><span>${formStep === 0 ? '1' : '✓'}</span>날짜와 동행자</li><li class="${formStep === 1 ? 'active' : ''}"><span>2</span>우리 가족의 여행 취향</li><li><span>3</span>여러 날의 일정과 동선</li></ol><div class="form-preset"><span class="tiny-label">지금 준비하는 여행</span><h3>${CASES[state.caseIndex].tag}</h3><p>${duration()} · 총 ${total()}명<br>${peopleLabel()}<br>그중 부모님·고령 동행자 ${state.seniors.length}명</p></div></div>
      <form id="trip-form" class="booking-card"><div class="booking-heading"><span class="step-count">0${formStep + 1} / 02</span><h2>${formStep === 0 ? '여행 기본 정보' : '가족별로 한 번 더 세심하게'}</h2><span class="pill">다낭 · 호이안</span></div>${formStep === 0 ? formBasics() : formProfiles()}<div class="form-actions">${formStep === 1 ? '<button type="button" class="secondary" id="form-prev">이전</button>' : '<span class="small muted">실제 예약 없이 여행을 설계해요.</span>'}<button class="primary" type="submit" id="form-submit">${formStep === 0 ? '가족의 취향 입력하기' : '우리 가족 일정 만들기'} ${icon('arrow', 18)}</button></div></form></div>`;
  updateChoiceSummary();
}
function formBasics() {
  return `<div class="form-row two"><label class="field"><span>출발일</span><input type="date" id="departure" value="${state.start}" min="2026-11-03" max="2027-12-31" required></label><label class="field"><span>몇 박 며칠 떠나나요?</span><select id="nights">${[2, 3, 4, 5].map((n) => `<option value="${n}" ${state.nights === n ? 'selected' : ''}>${n}박 ${n + 1}일</option>`).join('')}</select></label></div><div class="date-receipt">${icon('calendar', 17)} <strong>${dateLabel(0, true)} → ${dateLabel(state.nights, true)}</strong><span>현지 숙박 ${state.nights}박 · 낮 비행 일정 가정</span></div>
    <h3 class="field-heading">여행 인원 <span class="pill soft">총 ${total()}명</span></h3><div class="count-row"><div><strong>성인</strong><small>만 18세 이상 · 부모님도 포함해 주세요</small></div>${countControl('adults', state.adults, 1, 8)}</div><div class="count-row"><div><strong>어린이·청소년</strong><small>만 18세 미만 · 보호자와 함께</small></div>${countControl('children', state.children.length, 0, 6)}</div>
    ${state.children.length ? `<div class="age-inputs">${state.children.map((age, i) => `<label class="field"><span>자녀 ${i + 1} 나이</span><div class="unit-input"><input aria-label="자녀 ${i + 1} 나이" type="number" min="0" max="17" required value="${age}" data-child="${i}"><span>세</span></div></label>`).join('')}</div>` : ''}
    <div class="senior-count"><div class="count-row"><div><strong>그중 부모님·고령 동행자는?</strong><small>성인 인원에 포함 · 50세 이상 상세 프로필</small></div>${countControl('seniors', state.seniors.length, 0, state.adults)}</div><div class="inline-hint">${icon('info', 16)} ${state.seniors.length ? `성인 ${state.adults}명 중 ${state.seniors.length}명이에요. 총인원에 다시 더하지 않아요.` : '없어도 괜찮아요. 아이와 성인의 일정으로 준비해요.'}</div></div>`;
}
function choiceGroup(id, label, options, selected, multiple = false, attrs = '') {
  const values = Array.isArray(selected) ? selected : [selected];
  return `<fieldset class="choice-field"><legend>${label} <small>${multiple ? '여러 개 선택' : '하나 선택'}</small></legend><select id="${id}" ${multiple ? 'multiple' : ''} hidden ${attrs}>${Object.entries(options).map(([key, text]) => `<option value="${key}" ${values.includes(key) ? 'selected' : ''}>${text}</option>`).join('')}</select><div class="choice-chips">${Object.entries(options).map(([key, text]) => `<button type="button" class="choice-chip" data-choice="${id}" data-value="${key}" aria-pressed="${values.includes(key)}"><span class="chip-tick" aria-hidden="true">${values.includes(key) ? '✓' : '+'}</span>${text}</button>`).join('')}</div></fieldset>`;
}
function formProfiles() {
  return `${state.seniors.length ? state.seniors.map((person, i) => `<fieldset class="person-profile"><legend><span class="person-avatar">${i + 1}</span> 부모님·고령 동행자 ${i + 1}</legend><div class="form-row three"><label class="field"><span>호칭</span><input data-profile="${i}" data-key="name" value="${esc(person.name)}" maxlength="16" required></label><label class="field"><span>나이</span><div class="unit-input"><input type="number" data-profile="${i}" data-key="age" value="${person.age}" min="50" max="100" required><span>세</span></div></label><label class="field"><span>성별</span><select data-profile="${i}" data-key="gender">${selectOptions({ male: '남성', female: '여성' }, person.gender)}</select></label></div>${choiceGroup(`walk-${i}`, '평소 쉬지 않고 얼마나 걸으시나요?', { under_15min: '15분 이내', '15_30min': '15~30분', '30_60min': '30분~1시간', '1_2hour': '1~2시간', over_2hour: '2시간 이상', unknown: '잘 모르겠어요' }, person.walking_duration, false, `data-profile="${i}" data-key="walking_duration"`)}</fieldset>`).join('') : '<p class="empty-profile">부모님 프로필 없이 가족의 취향으로 여행을 준비해요.</p>'}
    ${choiceGroup('must', '꼭 경험하고 싶은 것', { beach: '미케 해변 산책', temple: '린응사 풍경', hoian: '호이안 등불 거리', craft: '공예 체험' }, state.musts, true)}
    <p class="small muted">선택한 경험은 모두 일정에 남겨요. 많이 고르면 일정이 길어질 수 있어요.</p>
    ${choiceGroup('avoid_conditions', '미리 확인하고 싶은 부담', { stairs: '계단·경사', long_walk: '긴 보행', queue: '긴 대기', heat: '더운 야외' }, state.avoid_conditions, true)}
    <p class="small muted">이 조건의 실제 정보는 아직 미확인이에요. 일정에서 직접 확인할 항목으로 안내해요.</p>
    ${choiceGroup('korean_need', '해외에서도 한식이 필요한가요?', FOOD_LABELS, state.korean_need)}
    ${choiceGroup('local_food', '새로운 현지 음식은 어떤가요?', { familiar: '익숙한 음식 위주', mixed: '현지식과 골고루', adventurous: '적극적으로 즐겨요', unknown: '잘 모르겠어요' }, state.local_food)}
    ${choiceGroup('venues', '어떤 식사 장소가 괜찮으세요?', { restaurant: '식당', street_food: '길거리 음식', unknown: '잘 모르겠어요' }, state.venues, true)}
    ${choiceGroup('ingredients', '피해야 하는 식재료', { seafood: '해산물', pork: '돼지고기', dairy: '유제품', nuts: '견과류' }, state.avoid_ingredients, true)}
    <label class="field"><span>그 밖에 피하는 음식</span><input id="avoid_other" value="${esc(state.avoid_other.join(', '))}" placeholder="예: 고수, 매운 음식" maxlength="100"></label>
    <div class="selection-summary" aria-live="polite"><span class="small-label">YOUR FAMILY'S PICKS</span><p id="choice-summary"></p></div><p class="inline-hint">${icon('info', 16)} 알레르기 대응과 실제 메뉴는 식당에 직접 확인해 주세요.</p>`;
}
function updateChoiceSummary() {
  const el = $('choice-summary');
  if (!el) return;
  const values = [...document.querySelectorAll('.choice-field select')].flatMap(select => [...select.selectedOptions].map(option => option.textContent));
  el.textContent = values.length ? values.join(' · ') : '원하는 항목을 골라보세요.';
  const preset = document.querySelector('.form-preset');
  if (preset) {
    let live = $('family-selection-live');
    if (!live) { live = document.createElement('div'); live.id = 'family-selection-live'; preset.append(live); }
    const experiences = [...$('must').selectedOptions].map(option => option.textContent);
    const checks = [...$('avoid_conditions').selectedOptions].map(option => option.textContent);
    live.innerHTML = `<span class="small-label">우리 가족의 선택</span><div>${experiences.map(text => `<span class="live-pick">${esc(text)}</span>`).join('') || '<small>꼭 하고 싶은 경험을 골라주세요.</small>'}</div>${checks.length ? `<p>확인할 부담 · ${checks.map(esc).join(' · ')}</p>` : ''}`;
  }
}
function readForm() {
  const form = $('trip-form');
  if (!form.reportValidity()) return false;
  if (formStep === 0) {
    state.start = $('departure').value;
    state.nights = Number($('nights').value);
    document
      .querySelectorAll('[data-child]')
      .forEach((input) => (state.children[Number(input.dataset.child)] = Number(input.value)));
  } else {
    document.querySelectorAll('[data-profile]').forEach((input) => {
      state.seniors[Number(input.dataset.profile)][input.dataset.key] =
        input.dataset.key === 'age' ? Number(input.value) : input.value.trim();
    });
    state.musts = [...$('must').selectedOptions].map(o => o.value);
    if (!state.musts.length) { toast('꼭 하고 싶은 경험을 하나 이상 골라주세요.'); $('must').nextElementSibling.querySelector('button').focus(); return false; }
    state.must = state.musts[0];
    state.avoid_conditions = [...$('avoid_conditions').selectedOptions].map(o => o.value);
    state.korean_need = $('korean_need').value;
    state.local_food = $('local_food').value;
    state.venues = [...$('venues').selectedOptions].map(o => o.value);
    if (!state.venues.length) state.venues = ['unknown'];
    state.avoid_other = $('avoid_other')
      .value.split(',')
      .map((value) => value.trim())
      .filter(Boolean)
      .slice(0, 10);
    state.avoid_ingredients = [...$('ingredients').selectedOptions].map(o => o.value);
  }
  return true;
}
async function generateTrip() {
  const token = ++requestVersion;
  $('form-submit').disabled = true;
  $('form-submit').textContent = '가족의 속도로 일정을 준비하고 있어요…';
  const results = await Promise.all(
    state.seniors.map(async (person) => {
      const payload = {
        age: person.age,
        gender: person.gender,
        walking_duration: person.walking_duration === 'unknown' ? null : person.walking_duration,
        local_food: state.local_food,
        korean_need: state.korean_need,
        avoid_ingredients: state.avoid_ingredients,
        avoid_other: state.avoid_other,
        venues: state.venues,
      };
      try {
        const response = await fetch('/api/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(3500),
        });
        if (!response.ok) throw new Error('profile');
        const result = await response.json();
        const speed = result.walking_speed?.base_speed_mps;
        if (!Number.isFinite(speed) || speed <= 0) throw new Error('mapping');
        return { name: person.name, ...result, source: 'api' };
      } catch {
        return { name: person.name, ...payload, walking_speed: null, source: 'demo' };
      }
    }),
  );
  if (token !== requestVersion || stage !== 'form') return;
  state.profiles = results;
  state.profileMode = !results.length
    ? 'not-needed'
    : results.every((r) => r.source === 'api')
      ? 'api'
      : 'demo';
  state.fixes = new Set();
  selectedDay = 1;
  view = 'day';
  selectedStop = null;
  stage = 'planner';
  renderPlanner();
  focusHeading();
}
function rawDays() {
  const first = ['airport', 'lunch', 'hotel', 'beach', 'dinner'];
  const city =
    state.caseId === 'nuclear'
      ? ['museum', 'market', 'lunch', 'pool', 'hotel']
      : ['beach', 'temple', 'market', 'lunch', 'hotel'];
  const excursion = ['hoian', ...(state.children.length ? ['craft'] : []), 'dinner', 'hotel'];
  const extras = [
    ['pool', 'lunch', 'museum', 'cafe', 'hotel'],
    ['beach', 'craft', 'lunch', 'pool', 'hotel'],
  ];
  const days = [{ title: '다낭에 도착하는 날', sub: '이동 뒤에는 서두르지 않기', ids: first }];
  for (let d = 1; d < state.nights; d++)
    days.push({
      title:
        d === 1
          ? '바다와 도시를 천천히'
          : d === 2
            ? '호이안에 등불이 켜지면'
            : '비워두어도 좋은 하루',
      sub:
        d === 1
          ? '우리 가족의 속도를 알아보는 하루'
          : d === 2
            ? '오후에 출발하는 작은 여행'
            : '체험과 휴식 사이, 여유롭게',
      ids: d === 1 ? [...city] : d === 2 ? [...excursion] : [...extras[(d - 3) % extras.length]],
    });
  days.push({
    title: '다시, 집으로 돌아가는 날',
    sub: '아침을 먹고 여유 있게 공항으로',
    ids: ['hotel', 'market', 'lunch', 'airport'],
  });
  for (const id of state.musts) if (!days.some(day => day.ids.includes(id))) days[1].ids.splice(1, 0, id);
  return days;
}
function itinerary(dayIndex, baseline = false) {
  const short = !baseline && state.fixes.has(`${dayIndex}-short`),
    rest = !baseline && state.fixes.has(`${dayIndex}-rest`);
  const raw = rawDays()[dayIndex],
    items = [];
  let time = dayIndex === 0 ? 11 * 60 : dayIndex === 2 ? 14 * 60 : 9 * 60;
  raw.ids.forEach((id, i) => {
    const p = PLACES[id];
    if (i) {
      const prev = PLACES[raw.ids[i - 1]],
        far = p.lat < 15.95 !== prev.lat < 15.95;
      const drive = far ? 50 : p.kind === 'hotel' && prev.kind === 'rest' ? 0 : 20;
      if (drive) {
        items.push({ kind: 'transfer', name: `차량 이동 약 ${drive}분`, minutes: drive, time });
        time += drive;
      }
    }
    if (id === 'lunch') time = Math.max(time, 12 * 60);
    if (id === 'dinner') time = Math.max(time, 18 * 60);
    if (id === 'hotel' && dayIndex === 0) time = Math.max(time, 14 * 60);
    if (id === 'airport' && dayIndex > 0) time = Math.max(time, 14 * 60);
    const meters = short ? p.short : p.meters;
    items.push({
      id,
      name: id === 'airport' ? `다낭 국제공항 · ${dayIndex === 0 ? '도착' : '귀국 수속'}` : p.name,
      kind: p.kind,
      meters,
      time,
      stay: p.stay,
      short: short && p.short < p.meters,
    });
    time += p.stay + walkMinutes(meters);
    if (rest && ['sight', 'activity'].includes(p.kind)) {
      items.push({
        id: 'cafe',
        name: '앉아서 쉬는 시간',
        kind: 'break',
        time,
        stay: 25,
        meters: 0,
      });
      time += 25;
    }
  });
  return items;
}
function speed() {
  if (!state.seniors.length) return state.children.length ? 0.9 : 1.1;
  return Math.min(...state.profiles.map((p) => p.walking_speed?.base_speed_mps || 0.8));
}
function walkMinutes(meters) {
  return Math.ceil(meters / speed() / 60);
}
function limit() {
  return state.seniors.length
    ? Math.min(...state.seniors.map((p) => WALK_LIMITS[p.walking_duration] || 20))
    : state.children.length
      ? 25
      : 40;
}
function evaluateDay(d, baseline = false) {
  const items = itinerary(d, baseline);
  let meters = 0,
    stretch = 0,
    max = 0,
    restCount = 0,
    burdens = 0;
  const problems = [];
  for (const item of items) {
    if (item.kind === 'transfer') continue; // 이동을 확실한 휴식으로 간주하지 않는 시연 가정
    if (['break', 'rest', 'meal', 'hotel'].includes(item.kind)) {
      max = Math.max(max, stretch);
      stretch = 0;
      burdens = 0;
      if (item.kind === 'break' || item.kind === 'rest') restCount++;
    } else {
      stretch += item.meters;
      max = Math.max(max, stretch);
      if (item.kind === 'sight') burdens++;
    }
    meters += item.meters || 0;
    if (burdens === 2 && !problems.some((p) => p.key === 'placement'))
      problems.push({
        key: 'placement',
        title: '관광지가 휴식 없이 이어져요',
        reason: '차량 이동 외에 앉아서 쉬는 시간을 넣어보세요.',
      });
  }
  const longest = walkMinutes(max);
  if (longest > limit())
    problems.unshift({
      key: 'walking',
      title: `연속 보행 ${longest}분, 우리 가족 기준보다 길어요`,
      reason: `시연 한도 ${limit()}분 · 관광지 내부에서 걷는 양을 합쳐 보았어요.`,
    });
  const totalWalk = walkMinutes(meters);
  return {
    items,
    totalWalk,
    longest,
    restCount,
    problems,
    unknown: new Set(items.filter((i) => i.id).map((i) => i.id)).size,
    meters,
  };
}
function tripMetrics(baseline = false) {
  return rawDays().reduce(
    (result, _, i) => {
      const d = evaluateDay(i, baseline);
      result.walk += d.totalWalk;
      result.problems += d.problems.length;
      result.rests += d.restCount;
      return result;
    },
    { walk: 0, problems: 0, rests: 0 },
  );
}
function timeLabel(min) {
  return `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`;
}
function renderPlanner() {
  disposeMap();
  const days = rawDays(),
    all = tripMetrics();
  $('app').innerHTML =
    `<div class="planner-page"><section class="trip-heading"><div><div class="eyebrow">우리 가족 여행 일정</div><h1>우리 가족의 <em>다낭 · 호이안</em></h1><div class="trip-meta"><span>${icon('calendar', 16)} ${dateLabel()} — ${dateLabel(state.nights)} <strong>${duration()}</strong></span><span>${icon('people', 16)} ${peopleLabel()} · 총 ${total()}명</span><button class="text-link" id="edit-trip">여행 정보 수정</button></div></div><div class="trip-tools"><button class="secondary" id="compare">전후 비교</button><button class="primary" id="share-trip">${icon('download', 17)} 여행 카드</button></div></section>
    <section class="family-ribbon"><div class="ribbon-icon">${icon(state.seniors.length ? 'parents' : 'kids', 24)}</div><div><strong>${state.seniors.length ? state.seniors.map((p) => `${esc(p.name)} ${p.age}세`).join(' · ') : `${state.children.length ? '아이들과 함께하는' : '성인끼리 떠나는'} 여행`}</strong><p>${state.seniors.length ? `${state.seniors.length}분의 생활형 답변 중 더 짧은 연속 보행 한도 ${limit()}분을 기준으로 살펴봐요.` : `부모님 프로필 없이 ${state.children.length ? '체험과 자유시간을 함께' : '관광과 휴식을 함께'} 담았어요.`}</p></div><div class="ribbon-status"><span class="status-light ${all.problems ? 'amber' : 'green'}"></span>${all.problems ? `조정할 구간 ${all.problems}개` : '시연 규칙 초과 없음'}<small>${state.profileMode === 'api' ? '프로필 API 연결됨' : state.profileMode === 'not-needed' ? '고령 동행자 없음' : '예시 프로필 · API 미연결'}</small></div></section>
    <section class="travel-basics" aria-label="숙박과 항공 일정 예시"><div>${icon('plane', 18)}<span><small>출국 · ${dateLabel()}</small><strong>한국 08:30 → 다낭 11:00</strong></span></div><div>${icon('bed', 18)}<span><small>현지 숙박</small><strong>같은 숙소에서 ${state.nights}박 연박</strong></span></div><div>${icon('plane', 18)}<span><small>귀국 · ${dateLabel(state.nights)}</small><strong>다낭 16:00 → 한국 22:30</strong></span></div><p>각 도시 현지 시각 · 항공편·숙소 미조회 · 시연을 위해 정한 시간입니다.</p></section>
    <div class="planner-toolbar"><div class="segmented"><button data-view="day" class="${view === 'day' ? 'active' : ''}">${icon('calendar', 16)} 하루씩 보기</button><button data-view="overview" class="${view === 'overview' ? 'active' : ''}">여행 한눈에</button></div><span class="small muted">${state.nights}박 같은 숙소 · 낮 출도착 가정 · 모든 일정은 예시</span></div>
    <div id="overview" ${view !== 'overview' ? 'hidden' : ''}></div>
    <div class="planner-grid ${view === 'overview' ? 'is-hidden' : ''}"><nav class="day-nav" aria-label="여행 날짜"><h2 class="day-column-heading">여행 날짜</h2>${days
      .map((day, i) => {
        const m = evaluateDay(i);
        return `<button data-day="${i}" ${i === selectedDay ? 'aria-current="date"' : ''}><span class="day-no">DAY ${String(i + 1).padStart(2, '0')}</span><strong>${dateLabel(i, true)}</strong><span class="day-theme">${day.title}</span><span class="day-mini"><span class="day-mini-bar"><i style="width:${Math.min(100, m.totalWalk)}%"></i></span>${m.totalWalk}분</span><small class="${m.problems.length ? 'warning-text' : 'success-text'}">${m.problems.length ? `조정 ${m.problems.length}개` : '시연 기준 내 · 확인 필요'}</small></button>`;
      })
      .join(
        '',
      )}<div class="day-nav-note">${icon('bed', 16)} 현지 숙박 ${state.nights}박<br>귀국일까지 ${days.length}일</div></nav>
      <section class="agenda-panel" id="agenda" aria-live="polite"></section>
      <aside class="map-panel"><div class="map-head"><div><span class="small-label">선택한 날짜의 방문 순서</span><h3>오늘의 동선</h3></div><button class="quiet mobile-map-close" id="close-map" aria-label="지도 닫기">${icon('close', 18)}</button><button class="quiet" id="fit-map" aria-label="오늘 동선 전체 보기">${icon('map', 18)} 전체</button></div><div class="map-wrap"><div id="map" aria-label="선택한 날짜의 관광지 위치 지도"></div><div id="map-fallback" hidden>지도 배경 연결이 원활하지 않아요.<br>장소 위치와 방문 순서는 계속 볼 수 있어요.</div></div><div class="map-caption"><span><i class="route-dash"></i> 방문 순서</span><small>점선은 실제 도로·도보 경로가 아니에요.</small></div><div class="map-selection" id="map-selection"><span>${icon('pin', 20)}</span><div><strong>일정과 지도가 함께 움직여요.</strong><p>장소 카드나 지도 번호를 눌러보세요.</p></div></div><div class="stay-card">${icon('bed', 24)}<div><strong>짐은 두고, 가볍게 다녀오기</strong><p>미케 해변 근처 숙소에 ${state.nights}박 연박<br>실제 숙소·엘리베이터는 확인이 필요해요.</p></div></div><button class="map-mobile-toggle secondary" id="back-agenda">일정으로 돌아가기 ${icon('arrow', 16)}</button></aside></div></div>`;
  if (view === 'overview') renderOverview();
  else {
    renderAgenda();
    initMap();
    const nav = document.querySelector('.day-nav'),
      active = nav.querySelector('[aria-current]');
    if (innerWidth <= 600 && active)
      nav.scrollLeft = Math.max(0, active.offsetLeft - nav.offsetLeft - 20);
  }
}
function renderAgenda() {
  const raw = rawDays()[selectedDay],
    m = evaluateDay(selectedDay),
    isShort = state.fixes.has(`${selectedDay}-short`),
    isRest = state.fixes.has(`${selectedDay}-rest`);
  $('agenda').innerHTML =
    `${selectedDay === 2 ? '<div class="day-photo"><img src="assets/hoi-an.jpg" alt="호이안 구시가지의 강변 풍경"><span>HOI AN · 오늘의 작은 여행</span></div>' : ''}<div class="agenda-title"><span class="pill soft">DAY ${selectedDay + 1} · ${dateLabel(selectedDay, true)}</span><button class="text-link mobile-map" id="show-map">${icon('map', 16)} 지도 보기</button><h2>${raw.title}</h2><p>${raw.sub}</p></div><div class="day-stats"><div>${icon('walk', 18)}<strong>${m.totalWalk}<small>분</small></strong><span>예시 보행</span></div><div>${icon('coffee', 18)}<strong>${m.restCount}<small>번</small></strong><span>쉬는 일정</span></div><div>${icon('pin', 18)}<strong>${m.items.filter((i) => ['sight', 'activity'].includes(i.kind)).length}<small>곳</small></strong><span>관광·체험</span></div></div>
    ${m.problems.length ? `<div class="insight-card"><div class="insight-label">${icon('spark', 16)} 반걸음이 살펴봤어요</div><h3>${m.problems[0].title}</h3><p>${m.problems[0].reason}</p><div class="fix-buttons"><button class="${isShort ? 'applied' : 'fix-button'}" data-fix="short">${icon(isShort ? 'check' : 'walk', 15)} ${isShort ? '짧은 코스 적용됨' : '같은 장소, 짧은 코스로'}</button><button class="${isRest ? 'applied' : 'fix-button'}" data-fix="rest">${icon(isRest ? 'check' : 'coffee', 15)} ${isRest ? '휴식 적용됨' : '중간에 앉아서 쉬기'}</button></div></div>` : `<div class="calm-card">${icon('check', 18)} <div><strong>${state.fixes.size ? '선택한 변경으로 다시 살펴봤어요.' : '시연 규칙 초과는 없지만, 확인할 정보가 남아 있어요.'}</strong><p>시연 보행·배치 기준 내 일정이에요. 미확인 정보는 남아 있어요.</p></div></div>`}
    ${isShort || isRest ? `<div class="applied-strip"><span>${icon('check', 14)} 변경 반영 · 필수 경험 유지</span><button class="text-link" id="undo-day">이 날 변경 취소</button></div>` : ''}
    <section class="verification-note"><strong>아직 확인하지 못했어요</strong><p>실제 보행 경로·계단·휴식 위치·영업시간을 조회하지 못했어요. 표시된 시간과 코스는 예시이며 적합도는 미확인이에요.</p><p>출발 전 공식 관광 안내나 현지 여행사에 우회로·앉아서 쉴 곳·이동 가능 여부를 직접 확인해 주세요.</p>${state.avoid_conditions.length ? `<p>우리 가족의 추가 확인 요청: ${state.avoid_conditions.map(key => ({stairs:"계단·경사",long_walk:"긴 보행",queue:"긴 대기",heat:"더운 야외"})[key]).join(" · ")} — 아직 평가하지 못했어요.</p>` : ""}</section><ol class="agenda-list">${m.items.map((item, index) => agendaItem(item, index)).join('')}</ol><div class="day-end">오늘도, 우리 가족의 속도로.<span>표시하지 않은 시간은 자유 시간 · 일정·거리·부담 판단은 가정값입니다.</span></div>`;
}
function agendaItem(item, index) {
  if (item.kind === 'transfer')
    return `<li class="transfer">${icon('car', 14)} ${item.name}<span>예상 · 교통 미반영</span></li>`;
  const place = PLACES[item.id],
    number = pinNumber(index),
    isRest = item.kind === 'break',
    kindLabels = {
      flight: '항공·이동',
      hotel: '숙소',
      sight: '관광',
      rest: '자유·휴식',
      meal: '식사',
      activity: '체험',
      break: '휴식 추가',
    };
  return `<li class="agenda-stop ${isRest ? 'rest-stop' : ''}" id="stop-${index}"><span class="agenda-time">${timeLabel(item.time)}</span><span class="stop-node ${isRest ? 'rest-node' : ''}">${isRest ? icon('coffee', 12) : number}</span><button class="stop-card ${selectedStop === index ? 'selected' : ''}" data-stop="${index}"><div class="stop-icon kind-${item.kind}">${icon(isRest ? 'coffee' : place.icon, 22)}</div><div class="stop-copy">${item.id === 'hoian' ? '<img class="place-preview" src="assets/hoi-an.jpg" alt="호이안 강변 풍경" loading="lazy">' : ''}<div class="stop-kicker">${kindLabels[item.kind]}${state.musts.includes(item.id) ? ' <span class="must-badge">꼭 하고 싶은 경험</span>' : ''}</div><h3>${item.name}</h3><p>${isRest ? '25분, 앉아서 쉬어요. 실제 쉴 곳은 확인이 필요해요.' : item.kind === 'meal' ? `${FOOD_LABELS[state.korean_need]} · 식재료 선호 반영 필요` : place.desc}</p><div class="stop-tags">${isRest ? '<span>25분 휴식</span>' : `<span>${icon('walk', 12)} 내부 ${item.meters}m · 약 ${walkMinutes(item.meters)}분</span><span>${item.stay}분 머무르기</span>`}${item.short ? '<span class="changed">짧은 코스</span>' : ''}</div></div><span class="card-chevron">↗</span></button></li>`;
}
function pinNumber(index) {
  return evaluateDay(selectedDay)
    .items.slice(0, index + 1)
    .filter((item) => item.kind !== 'transfer' && item.kind !== 'break').length;
}
function renderOverview() {
  const days = rawDays();
  $('overview').innerHTML =
    `<div class="overview-intro"><h2>${duration()}, 한 장에 펼쳐보기.</h2><p>도착과 귀국도 여행의 일부. 하루를 누르면 그날의 일정과 지도로 이동해요.</p></div><div class="overview-grid">${days
      .map((day, i) => {
        const m = evaluateDay(i);
        return `<button class="overview-day" data-overview-day="${i}"><div class="overview-day-top"><span>DAY 0${i + 1}</span><strong>${dateLabel(i, true)}</strong></div><h3>${day.title}</h3><div class="overview-timeline">${day.ids.map((id) => `<div><span class="overview-dot">${icon(PLACES[id].icon, 13)}</span>${PLACES[id].name}${state.musts.includes(id) ? ' <span class="must-dot">★</span>' : ''}</div>`).join('')}</div><div class="overview-footer"><span>보행 약 ${m.totalWalk}분</span><strong class="${m.problems.length ? 'warning-text' : 'success-text'}">${m.problems.length ? `조정 ${m.problems.length}개` : '확인 필요'}</strong></div></button>`;
      })
      .join('')}</div>`;
}
function initMap() {
  if (typeof L === 'undefined') {
    $('map').innerHTML =
      '<p class="map-unavailable">지도를 불러올 수 없어요. 일정 카드에서 장소를 확인해 주세요.</p>';
    return;
  }
  map = L.map('map', { scrollWheelZoom: false, zoomControl: false }).setView([16.065, 108.24], 12);
  L.control.zoom({ position: 'topright' }).addTo(map);
  const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  let loaded = false;
  tiles.on('tileload', () => {
    loaded = true;
    if ($('map-fallback')) $('map-fallback').hidden = true;
  });
  tiles.on('tileerror', () => {
    if (!loaded && $('map-fallback')) $('map-fallback').hidden = false;
  });
  mapGroup = L.featureGroup().addTo(map);
  const items = evaluateDay(selectedDay).items;
  const coordinates = [];
  items.forEach((item, index) => {
    if (!item.id || item.kind === 'break') return;
    const p = PLACES[item.id],
      point = [p.lat, p.lng];
    coordinates.push(point);
    const marker = L.marker(point, {
      icon: L.divIcon({
        className: 'number-marker',
        html: `<span><b>${pinNumber(index)}</b></span>`,
        iconSize: [32, 38],
        iconAnchor: [16, 38],
      }),
      title: p.name,
      keyboard: true,
    }).addTo(mapGroup);
    marker.bindTooltip(p.name, { direction: 'top', offset: [0, -34] });
    marker.on('click', () => selectStop(index, false));
    markers.push({ marker, index });
  });
  if (coordinates.length > 1)
    L.polyline(coordinates, { color: '#7247bb', weight: 3, dashArray: '5 9', opacity: 0.8 }).addTo(
      mapGroup,
    );
  fitMap();
  map.whenReady(() => requestAnimationFrame(() => map?.invalidateSize()));
}
function fitMap() {
  if (map && mapGroup?.getLayers().length)
    map.fitBounds(mapGroup.getBounds().pad(0.25), { maxZoom: 14, animate: false });
}
function selectStop(index, pan = true) {
  const item = evaluateDay(selectedDay).items[index];
  if (!item) return;
  if (item.kind === 'break') {
    openPlace(item);
    return;
  }
  selectedStop = index;
  document
    .querySelectorAll('.stop-card')
    .forEach((el) => el.classList.toggle('selected', Number(el.dataset.stop) === index));
  const p = PLACES[item.id];
  if (map && pan) map.panTo([p.lat, p.lng]);
  markers.forEach(({ marker, index: idx }) => {
    marker.getElement()?.classList.toggle('active', idx === index);
    if (idx === index) marker.openTooltip();
  });
  $('map-selection').innerHTML =
    `<span>${icon(p.icon, 23)}</span><div><strong>${p.name}</strong><p>내부 보행 ${item.meters}m · 약 ${walkMinutes(item.meters)}분</p><button class="text-link" data-detail="${index}">근거·미확인 정보 보기 ↗</button></div>`;
  if (!pan) $(`stop-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  if (window.innerWidth < 900 && pan) openPlace(item);
}
function openPlace(item) {
  const p = PLACES[item.id];
  $('detail-body').innerHTML =
    `<div class="modal-header"><span class="small-label">PLACE DETAILS</span><button class="icon-button" data-close="detail" aria-label="닫기">${icon('close')}</button></div><div class="detail-place-icon">${icon(p.icon, 36)}</div><h2>${item.kind === 'break' ? item.name : p.name}</h2><p class="muted">${p.en}</p><p class="detail-description">${p.desc}</p><div class="detail-metrics"><span>내부 보행 <strong>${item.meters}m</strong></span><span>보행 시간 <strong>약 ${walkMinutes(item.meters)}분</strong></span></div><div class="detail-callout"><strong>확인이 필요한 정보</strong><p>${p.unknown}</p></div><dl class="detail-evidence"><dt>평가·거리 자료</dt><dd>화면 시연용 고정 데이터 · 외부 검수 전</dd><dt>장소 부담</dt><dd>${p.burden || '별도 평가 미확인'}</dd><dt>지도 좌표</dt><dd>장소 부근의 대략적 위치 · 출입구 위치 아님</dd><dt>실제 도로 경로</dt><dd>조회하지 않음 · 지도 점선은 방문 순서</dd><dt>우리 가족의 속도</dt><dd>${state.profileMode === 'api' ? '프로필 API의 연령·성별 평균값 중 최솟값' : '시연용 가정 속도'} ${speed().toFixed(2)}m/s</dd></dl><p class="small muted">연령 평균값은 개인의 실제 보행 능력을 보장하지 않습니다. 생활형 답변은 별도의 시연 보행 한도에 반영합니다.</p>`;
  if (!$('detail').open) $('detail').showModal();
}
function compare() {
  const before = tripMetrics(true),
    after = tripMetrics();
  $('detail-body').innerHTML =
    `<div class="modal-header"><span class="small-label">SAME TRIP, A DIFFERENT PACE</span><button class="icon-button" data-close="detail" aria-label="닫기">${icon('close')}</button></div><h2>원하는 경험은 남기고,<br>무리한 걸음은 덜어내고.</h2><p class="muted">${duration()} · 총 ${total()}명 · 같은 가족 프로필로 비교했어요.</p><div class="compare-table"><div><span>전체 여행</span><strong>수정 전</strong><strong>현재 일정</strong></div>${[
      ['전체 보행', before.walk + '분', after.walk + '분'],
      ['조정할 구간', before.problems + '개', after.problems + '개'],
      ['쉬는 일정', before.rests + '번', after.rests + '번'],
      ['꼭 하고 싶은 경험', state.musts.map(id => PLACES[id].name).join(' · '), '모두 유지'],
      ['미확인 장소 정보', '확인 필요', '여전히 확인 필요'],
    ]
      .map(
        (row) =>
          `<div>${row.map((t, i) => `<${i ? 'strong' : 'span'}>${t}</${i ? 'strong' : 'span'}>`).join('')}</div>`,
      )
      .join('')}</div><div class="compare-day-bars">${rawDays()
      .map((day, i) => {
        const b = evaluateDay(i, true),
          a = evaluateDay(i);
        return `<div><span>DAY ${i + 1}</span><div><i style="width:${Math.max(3, b.totalWalk)}%"></i><b style="width:${Math.max(3, a.totalWalk)}%"></b></div><strong>${b.totalWalk} → ${a.totalWalk}분</strong></div>`;
      })
      .join(
        '',
      )}</div><p class="small muted">휴식은 연속 보행을 끊고, 짧은 코스는 예시 보행량을 줄여요. 보행 시간·규칙 한도는 시연 가정이며 실제 안전성 판단이 아닙니다.</p>`;
  $('detail').showModal();
}
function share(cardDay = selectedDay) {
  const m = evaluateDay(cardDay);
  $('share-body').innerHTML =
    `<div class="modal-header"><span class="small-label">A LITTLE LETTER FOR OUR FAMILY</span><button class="icon-button" data-close="share" aria-label="닫기">${icon('close')}</button></div><h2>함께 볼 여행 안내서.</h2><p class="muted">${dateLabel()} — ${dateLabel(state.nights)} · ${duration()} · 총 ${total()}명</p><div class="card-day-tabs">${rawDays()
      .map(
        (_, i) =>
          `<button data-card-day="${i}" class="${i === cardDay ? 'active' : ''}">DAY ${i + 1}</button>`,
      )
      .join(
        '',
      )}</div><div class="family-travel-card"><div class="family-card-heading"><span>다낭 · 호이안 / DAY ${cardDay + 1}</span><h3>${rawDays()[cardDay].title}</h3><p>${dateLabel(cardDay, true)}</p></div><div class="family-card-body"><p>오늘은 약 <strong>${m.totalWalk}분</strong> 걸어요.<br>${m.restCount ? `쉬는 일정은 ${m.restCount}번이에요.` : '이동과 식사 사이에 여유를 둘게요.'}</p><ol>${m.items
      .filter((item) => item.kind !== 'transfer')
      .map((item) => `<li><span>${timeLabel(item.time)}</span>${item.name}</li>`)
      .join(
        '',
      )}</ol><p class="small">${FOOD_LABELS[state.korean_need]}<br>실제 경로·계단·휴식 위치·식당은 미확인이에요. 출발 전 공식 안내나 현지 여행사에 직접 확인해 주세요.</p></div></div><div class="share-actions"><button class="primary" data-download="${cardDay}">${icon('download', 18)} 이 날 카드 저장</button><button class="secondary" id="download-all">전체 여행 안내서 저장</button></div><p class="small muted">실제 파일로 저장됩니다. 외부 메신저 전송이나 예약은 하지 않습니다.</p>`;
  if (!$('share').open) $('share').showModal();
}
function downloadFile(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('여행 안내서를 저장했어요.');
}
function downloadCard(d) {
  const m = evaluateDay(d),
    lines = [
      `${duration()} · 다낭 · 호이안`,
      `${dateLabel(d, true)} · DAY ${d + 1}`,
      rawDays()[d].title,
      `총 ${total()}명 · 오늘 걸음 약 ${m.totalWalk}분`,
      ...m.items.filter((i) => i.kind !== 'transfer').map((i) => `${timeLabel(i.time)} ${i.name}`),
      FOOD_LABELS[state.korean_need],
      '미확인: 실제 경로·계단·휴식 위치·영업시간',
      '공식 관광 안내·현지 여행사에 직접 확인해 주세요.',
      '시연용 예시 일정 · 예약 확인서 아님',
    ];
  const chunks = lines.flatMap((t) => Array.from(t.matchAll(/.{1,24}/gu), (m) => m[0]));
  const height = 120 + chunks.length * 46;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="780" height="${height}"><rect width="780" height="${height}" fill="#f4eefb"/>${chunks.map((t, i) => `<text x="40" y="${70 + i * 46}" font-family="sans-serif" font-size="${i === 0 ? 34 : 26}" fill="#30223e">${esc(t)}</text>`).join('')}</svg>`;
  downloadFile(`반걸음-${duration()}-DAY${d + 1}.svg`, svg, 'image/svg+xml;charset=utf-8');
}
function downloadAll() {
  const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><title>우리 가족의 다낭 여행</title><style>body{font:20px/1.8 sans-serif;color:#30223e;max-width:780px;margin:40px auto;padding:24px}section{break-inside:avoid;border-top:2px solid #eee;padding:24px 0}li{padding:8px 0}span{color:#6a3faf;margin-right:16px}small{font-size:16px}</style><h1>우리 가족의 다낭 · 호이안</h1><p>${dateLabel()} — ${dateLabel(state.nights)} · ${duration()} · 총 ${total()}명</p>${rawDays()
    .map(
      (day, d) =>
        `<section><h2>DAY ${d + 1} · ${dateLabel(d, true)}</h2><h3>${day.title}</h3><p>걷기 약 ${evaluateDay(d).totalWalk}분 · ${FOOD_LABELS[state.korean_need]}</p><ol>${itinerary(
          d,
        )
          .filter((i) => i.kind !== 'transfer')
          .map((i) => `<li><span>${timeLabel(i.time)}</span>${i.name}</li>`)
          .join('')}</ol></section>`,
    )
    .join(
      '',
    )}<small>모든 일정·거리·시간은 가정값입니다. 실제 예약 내역이 아닙니다. 실제 경로·계단·휴식 위치·영업시간은 조회하지 못했습니다. 출발 전 공식 관광 안내나 현지 여행사에 직접 확인해 주세요.</small></html>`;
  downloadFile(`반걸음-${duration()}-전체안내서.html`, html, 'text/html;charset=utf-8');
}
function sources() {
  $('detail-body').innerHTML =
    `<div class="modal-header"><span class="small-label">ABOUT THIS DEMO</span><button class="icon-button" data-close="detail" aria-label="닫기">${icon('close')}</button></div><h2>자료와 시연 범위</h2><div class="source-section"><h3>기획</h3><p><a href="https://app.notion.com/p/752b00a36e9b8202bf8881020206725c" target="_blank" rel="noopener">팀 기획·보완 설명</a>을 바탕으로 만들었어요. 입력은 <a href="https://m.hanatour.com/trp/pkg/CHPC0PKG0200M100?pkgCd=AVB235261012VJF" target="_blank" rel="noopener">하나투어의 여행 인원 선택</a>을 참고했어요.</p><h3>실제로 연결한 기능</h3><p>같은 서버의 POST /api/profile, Leaflet 지도, OSM 지도 타일, 카드·전체 안내서 다운로드. 지도 좌표는 대략적 위치이며 실제 길찾기가 아니에요.</p><h3>시연용으로 만든 데이터</h3><p>관광지 내부 거리·짧은 코스·체류 시간·이동 시간·부담 등급·보행 한도는 모두 가정값이에요. 항공·숙소·식당 검색, DB 저장, 예약은 연결하지 않았어요. Google Places 데이터나 리뷰를 OSM 지도에 표시하지 않아요.</p><h3>보행 계산</h3><p>프로필 API는 건강한 인구의 나이·성별 평균 속도를 반환해요. 생활형 답변은 별도 시연 한도에만 반영하며, 속도를 의학적으로 보정하지 않아요. API 연결 실패 시 0.8m/s 가정값과 미연결 표시를 사용해요.</p><h3>이미지·지도</h3><p>호이안 사진: <a href="https://vietnam.travel/things-to-do/hoi-an-world%E2%80%99s-top-%E2%80%9Chidden-gem%E2%80%9D-city" target="_blank" rel="noopener">Vietnam Tourism</a> · 지도: © OpenStreetMap contributors · Leaflet BSD-2-Clause.</p><p>새로고침하면 입력과 수정 상태가 초기화돼요. 지도 타일은 인터넷 연결이 필요하며, 연결 실패 시 위치 번호와 방문 순서는 유지돼요.</p></div>`;
  $('detail').showModal();
}
function updateCounter(key, delta) {
  if (!readForm()) return;
  if (key === 'adults') {
    state.adults = Math.max(1, Math.min(8, state.adults + delta));
    if (state.seniors.length > state.adults) state.seniors.length = state.adults;
  }
  if (key === 'children') {
    if (delta > 0 && state.children.length < 6) state.children.push(9);
    else if (delta < 0) state.children.pop();
  }
  if (key === 'seniors') {
    if (delta > 0 && state.seniors.length < state.adults)
      state.seniors.push({
        name: `동행자 ${state.seniors.length + 1}`,
        age: 65,
        gender: 'female',
        walking_duration: '15_30min',
      });
    else if (delta < 0) state.seniors.pop();
  }
  renderForm();
  const selector = `[data-count="${key}"][data-delta="${delta}"]`;
  document.querySelector(selector)?.focus();
}
$('app').addEventListener('submit', (event) => {
  if (event.target.id !== 'trip-form') return;
  event.preventDefault();
  if (!readForm()) return;
  if (formStep === 0) {
    formStep = 1;
    renderForm();
    focusHeading();
  } else generateTrip();
});
document.addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!button || button.disabled) return;
  if (button.dataset.choice) {
    const select = $(button.dataset.choice);
    const option = [...select.options].find(o => o.value === button.dataset.value);
    if (select.multiple) {
      option.selected = !option.selected;
      if (select.id === 'venues') [...select.options].forEach(o => { if (option.selected && (option.value === 'unknown' ? o !== option : o.value === 'unknown')) o.selected = false; });
    } else select.value = option.value;
    select.nextElementSibling.querySelectorAll('[data-choice]').forEach(b => { const selected = [...select.selectedOptions].some(o => o.value === b.dataset.value); b.setAttribute('aria-pressed', String(selected)); b.querySelector('.chip-tick').textContent = selected ? '✓' : '+'; });
    updateChoiceSummary();
    return;
  }
  if (button.dataset.start !== undefined) return start(Number(button.dataset.start));
  if (button.id === 'home' || button.id === 'back-home') {
    requestVersion++;
    landing();
    focusHeading();
    return;
  }
  if (button.dataset.count)
    return updateCounter(button.dataset.count, Number(button.dataset.delta));
  if (button.id === 'form-prev') {
    if (!readForm()) return;
    formStep = 0;
    renderForm();
    return;
  }
  if (button.id === 'edit-trip') {
    requestVersion++;
    stage = 'form';
    formStep = 0;
    renderForm();
    focusHeading();
    return;
  }
  if (button.dataset.day !== undefined || button.dataset.overviewDay !== undefined) {
    selectedDay = Number(button.dataset.day ?? button.dataset.overviewDay);
    view = 'day';
    selectedStop = null;
    renderPlanner();
    return;
  }
  if (button.dataset.view) {
    view = button.dataset.view;
    renderPlanner();
    return;
  }
  if (button.dataset.fix) {
    state.fixes.add(`${selectedDay}-${button.dataset.fix}`);
    renderPlanner();
    toast('이 날 일정을 바꾸고 다시 확인했어요.');
    return;
  }
  if (button.id === 'undo-day') {
    state.fixes.delete(`${selectedDay}-short`);
    state.fixes.delete(`${selectedDay}-rest`);
    renderPlanner();
    return;
  }
  if (button.dataset.stop !== undefined) return selectStop(Number(button.dataset.stop));
  if (button.dataset.detail !== undefined)
    return openPlace(evaluateDay(selectedDay).items[Number(button.dataset.detail)]);
  if (button.id === 'show-map') {
    document.querySelector('.map-panel').classList.add('mobile-open');
    setTimeout(() => {
      if (!document.querySelector('.map-panel.mobile-open')) return;
      map?.invalidateSize();
      fitMap();
      $('close-map')?.focus();
    }, 100);
    return;
  }
  if (button.id === 'fit-map') return fitMap();
  if (button.id === 'compare') return compare();
  if (button.id === 'share-trip') return share();
  if (button.dataset.cardDay !== undefined) return share(Number(button.dataset.cardDay));
  if (button.dataset.download !== undefined) return downloadCard(Number(button.dataset.download));
  if (button.id === 'download-all') return downloadAll();
  if (button.dataset.close) {
    $(button.dataset.close).close();
    return;
  }
  if (button.id === 'sources') return sources();
  if (button.id === 'back-agenda' || button.id === 'close-map') {
    closeMobileMap();
    return;
  }
});
$('app').addEventListener('change', (event) => {
  if (event.target.id === 'departure' || event.target.id === 'nights') {
    if (readForm()) renderForm();
  }
});
for (const id of ['detail', 'share'])
  $(id).addEventListener('click', (event) => {
    if (event.target === $(id)) {
      const rect = $(id).getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
        $(id).close();
    }
  });
landing();

function closeMobileMap() {
  document.querySelector('.map-panel')?.classList.remove('mobile-open');
  $('show-map')?.focus();
}
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && document.querySelector('.map-panel.mobile-open')) closeMobileMap();
});
