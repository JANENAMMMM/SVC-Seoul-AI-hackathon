import { useId, useRef, useState } from 'react';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';

export function Button({ variant = 'primary', className = '', type = 'button', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) {
  return <button type={type} className={`bg-button ${variant === 'secondary' ? 'bg-button--secondary' : ''} ${className}`} {...props} />;
}

export function Field({ label, hint, error, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  const generated = useId();
  const inputId = id ?? generated;
  const description = [hint && `${inputId}-hint`, error && `${inputId}-error`, props['aria-describedby']].filter(Boolean).join(' ') || undefined;
  return <div className="bg-field">
    <label htmlFor={inputId}>{label}</label>
    <input {...props} id={inputId} className={`bg-input ${props.className ?? ''}`} aria-invalid={error ? true : props['aria-invalid']} aria-describedby={description} />
    {hint && <span id={`${inputId}-hint`} className="bg-hint">{hint}</span>}
    {error && <span id={`${inputId}-error`} className="bg-hint bg-error">{error}</span>}
  </div>;
}

export function ChoiceGroup({ legend, name, options, value, onChange }: { legend: string; name: string; options: { value: string; label: string }[]; value: string; onChange: (value: string) => void }) {
  return <fieldset className="bg-choice-group"><legend>{legend}</legend><div className="bg-choices">
    {options.map(option => <label className="bg-choice" key={option.value}><input type="radio" name={name} value={option.value} checked={value === option.value} onChange={() => onChange(option.value)} /><span>{option.label}</span></label>)}
  </div></fieldset>;
}

export function Tabs({ items, label }: { label: string; items: { id: string; label: string; content: ReactNode }[] }) {
  const prefix = useId();
  const [selected, setSelected] = useState(items[0]?.id);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const active = items.some(item => item.id === selected) ? selected : items[0]?.id;
  return <div><div className="bg-tabs" role="tablist" aria-label={label}>
    {items.map((item, i) => <button type="button" role="tab" className="bg-tab" key={item.id}
      id={`${prefix}-tab-${item.id}`} aria-controls={`${prefix}-panel-${item.id}`} aria-selected={active === item.id}
      tabIndex={active === item.id ? 0 : -1} ref={el => { refs.current[i] = el; }} onClick={() => setSelected(item.id)}
      onKeyDown={event => {
        const next = event.key === 'ArrowRight' ? (i + 1) % items.length : event.key === 'ArrowLeft' ? (i - 1 + items.length) % items.length : event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : null;
        if (next !== null) { event.preventDefault(); setSelected(items[next].id); refs.current[next]?.focus(); }
      }}>{item.label}</button>)}
  </div>{items.map(item => <div key={item.id} role="tabpanel" tabIndex={0} id={`${prefix}-panel-${item.id}`} aria-labelledby={`${prefix}-tab-${item.id}`} hidden={active !== item.id}>{item.content}</div>)}</div>;
}

export function Badge({ children, tone = 'brand' }: { children: ReactNode; tone?: 'brand' | 'success' }) {
  return <span className={`bg-badge ${tone === 'success' ? 'bg-badge--success' : ''}`}>{children}</span>;
}

export function TripCard({ title, description, image, badges, price, href }: { title: string; description: string; image?: { src: string; alt: string }; badges?: ReactNode; price?: number; href: string }) {
  return <article className="bg-card">{image && <img className="bg-card-image" src={image.src} alt={image.alt} loading="lazy" />}<div className="bg-card-body">
    {badges && <div className="bg-badges">{badges}</div>}<h3>{title}</h3><p className="bg-hint">{description}</p>
    {price !== undefined && <div className="bg-price">{price.toLocaleString('ko-KR')}<small> 원부터 / 1인</small></div>}
    <a className="bg-button bg-button--secondary" href={href} aria-label={`${title} 일정 살펴보기`}>일정 살펴보기</a>
  </div></article>;
}

export function StatCard({ label, value }: { label: string; value: string }) {
  return <dl className="bg-stat"><dt>{label}</dt><dd>{value}</dd></dl>;
}

export function Notice({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'warning' }) {
  return <div className={`bg-notice ${tone === 'warning' ? 'bg-notice--warning' : ''}`}>{children}</div>;
}

export function PageHeader({ children, homeHref = '/' }: { children?: ReactNode; homeHref?: string }) {
  return <header className="bg-header"><a className="bg-wordmark" href={homeHref}>반걸음</a>{children}</header>;
}

export function BottomNav({ items }: { items: { label: string; href: string; active?: boolean }[] }) {
  return <nav className="bg-bottom-nav" aria-label="주요 메뉴">{items.map(item => <a key={item.href} href={item.href} aria-current={item.active ? 'page' : undefined}>{item.label}</a>)}</nav>;
}
