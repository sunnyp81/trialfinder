export const siteConfig = {
  name: 'ClinicalTrialHub',
  tagline: 'Clinical trials, in plain English.',
  url: 'https://clinicaltrialhub.org',
  description: 'Find clinical trials explained in plain English. We translate complex eligibility criteria so you can quickly see if a trial might be right for you or someone you love.',
  staticFormsKey: 'YOUR_STATIC_FORMS_KEY',
  supportAffiliateUrl: '#',
  telehealthAffiliateUrl: '#',
} as const;

export const nav = [
  { label: 'Find a Trial', href: '/' },
  { label: 'Conditions', href: '/conditions/' },
  { label: 'Guides', href: '/guides/' },
  { label: 'Glossary', href: '/glossary/' },
  { label: 'FAQ', href: '/faq/' },
] as const;

export const conditionCategories = [
  {
    name: 'Cancer',
    keywords: ['cancer', 'carcinoma', 'neoplasm', 'tumor', 'lymphoma', 'leukemia', 'melanoma', 'sarcoma', 'myeloma', 'glioblastoma', 'glioma'],
  },
  {
    name: 'Heart & Blood',
    keywords: ['heart', 'cardiac', 'cardiovascular', 'atrial', 'coronary', 'hypertension', 'anemia', 'thrombosis', 'stroke', 'vascular'],
  },
  {
    name: 'Brain & Nerves',
    keywords: ['alzheimer', 'parkinson', 'epilepsy', 'multiple sclerosis', 'neuropathy', 'migraine', 'dementia', 'brain', 'neurolog'],
  },
  {
    name: 'Immune & Inflammatory',
    keywords: ['lupus', 'arthritis', 'crohn', 'colitis', 'psoriasis', 'eczema', 'dermatitis', 'inflammatory', 'autoimmune', 'asthma'],
  },
  {
    name: 'Diabetes & Metabolism',
    keywords: ['diabetes', 'obesity', 'metabolic', 'thyroid', 'insulin', 'cholesterol'],
  },
  {
    name: 'Rare Diseases',
    keywords: ['rare', 'genetic', 'hereditary', 'congenital', 'cystic fibrosis', 'sickle cell', 'muscular dystrophy'],
  },
  {
    name: 'Mental Health',
    keywords: ['depression', 'depressive', 'anxiety', 'bipolar', 'schizophrenia', 'ptsd', 'adhd', 'autism', 'psychiatric'],
  },
  {
    name: 'Infectious Disease',
    keywords: ['hiv', 'hepatitis', 'tuberculosis', 'covid', 'infection', 'viral', 'bacterial', 'sepsis'],
  },
] as const;

export function categorizeCondition(name: string): string {
  const lower = name.toLowerCase();
  for (const cat of conditionCategories) {
    for (const kw of cat.keywords) {
      if (lower.includes(kw)) return cat.name;
    }
  }
  return 'Other';
}

export function formatPhase(phase: string): string {
  if (!phase || phase === 'Not Applicable') return 'N/A';
  return phase
    .replace('PHASE1', 'Phase 1')
    .replace('PHASE2', 'Phase 2')
    .replace('PHASE3', 'Phase 3')
    .replace('PHASE4', 'Phase 4')
    .replace('EARLY_PHASE1', 'Early Phase 1')
    .replace(', ', ' / ');
}

export function formatStatus(status: string): { label: string; class: string } {
  if (status === 'RECRUITING') return { label: 'Now Recruiting', class: 'badge-recruiting' };
  if (status === 'NOT_YET_RECRUITING') return { label: 'Enrolling Soon', class: 'badge-enrolling' };
  return { label: status, class: 'badge-closed' };
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 2) {
      const d = new Date(`${dateStr}-01`);
      return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export function sexDisplay(sex: string): string {
  if (sex === 'ALL') return 'All genders';
  if (sex === 'MALE') return 'Males only';
  if (sex === 'FEMALE') return 'Females only';
  return sex;
}

export function ageDisplay(min: string, max: string): string {
  if (!min && !max) return 'All ages';
  if (min && max) return `${min} to ${max}`;
  if (min) return `${min}+`;
  return `Up to ${max}`;
}

export const phaseSafetyTemplates: Record<string, string> = {
  'EARLY_PHASE1': 'This is an early Phase 1 trial — the first time this treatment is tested in people. The primary goal is to check safety and find the right dose. Groups are small.',
  'PHASE1': 'This is a Phase 1 trial — an early-stage study focused on safety and dosing. Groups are usually small (20–80 people).',
  'PHASE2': 'This is a Phase 2 trial — the treatment has passed initial safety testing and is now being studied for effectiveness. Groups are typically 100–300 people.',
  'PHASE3': 'This is a Phase 3 trial — a large-scale study comparing this treatment to the current standard of care. These trials often involve hundreds or thousands of participants.',
  'PHASE4': 'This is a Phase 4 trial — the treatment is already approved and available. This study is monitoring long-term safety and effectiveness.',
};
