import { siteConfig } from './site-config';

export function buildWebSiteSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: siteConfig.name,
    url: siteConfig.url,
    description: siteConfig.description,
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${siteConfig.url}/condition/{search_term_string}/`,
      },
      'query-input': 'required name=search_term_string',
    },
  };
}

export function buildOrganizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: siteConfig.name,
    url: siteConfig.url,
    description: siteConfig.description,
  };
}

export function buildBreadcrumbSchema(items: { name: string; url: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

export function buildMedicalTrialSchema(trial: {
  briefTitle: string;
  status: string;
  phase: string;
  conditions: string[];
  nctId: string;
  plainSummary?: string;
  startDate?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'MedicalTrial',
    name: trial.briefTitle,
    trialDesign: trial.phase,
    status: trial.status === 'RECRUITING' ? 'ActiveNotRecruiting' : 'NotYetRecruiting',
    healthCondition: trial.conditions.map(c => ({
      '@type': 'MedicalCondition',
      name: c,
    })),
    identifier: {
      '@type': 'PropertyValue',
      propertyID: 'NCT ID',
      value: trial.nctId,
    },
    description: trial.plainSummary || '',
    ...(trial.startDate ? { startDate: trial.startDate } : {}),
    url: `${siteConfig.url}/trial/${trial.nctId.toLowerCase()}/`,
  };
}

export function buildMedicalConditionSchema(condition: {
  name: string;
  slug: string;
  trialCount: number;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'MedicalCondition',
    name: condition.name,
    url: `${siteConfig.url}/condition/${condition.slug}/`,
  };
}

export function buildFAQSchema(faqs: { question: string; answer: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(faq => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };
}

export function buildItemListSchema(items: { name: string; url: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    numberOfItems: items.length,
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      url: item.url,
    })),
  };
}

export function buildArticleSchema(opts: {
  title: string;
  description: string;
  url: string;
  datePublished?: string;
  dateModified?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: opts.title,
    description: opts.description,
    url: opts.url,
    author: {
      '@type': 'Organization',
      name: siteConfig.name,
    },
    publisher: {
      '@type': 'Organization',
      name: siteConfig.name,
    },
    ...(opts.datePublished ? { datePublished: opts.datePublished } : {}),
    ...(opts.dateModified ? { dateModified: opts.dateModified } : {}),
  };
}
