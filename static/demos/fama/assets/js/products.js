/* FAMA — داده‌های نمونه محصولات (برای راه‌اندازی اولیه)
   بعداً این فایل با محصولات واقعی یا API فروشگاه جایگزین می‌شود. */

const FAMA_CATEGORIES = [
  { id: 'lips',     name: 'آرایش لب',      icon: 'lipstick' },
  { id: 'eyes',     name: 'آرایش چشم',     icon: 'mascara' },
  { id: 'face',     name: 'آرایش صورت',    icon: 'foundation' },
  { id: 'skincare', name: 'مراقبت پوست',   icon: 'serum' },
  { id: 'fragrance',name: 'عطر و بدن',     icon: 'perfume' },
  { id: 'tools',    name: 'ابزار آرایشی',  icon: 'brush' },
];

const FAMA_PRODUCTS = [
  {
    id: 1, name: 'رژ لب مایع مات فاما — رنگ رز کلاسیک', cat: 'lips',
    price: 485000, oldPrice: 590000, rating: 4.8, reviews: 124,
    badge: 'sale', art: 'lipstick', hue: ['#F472B6', '#BE185D'],
    desc: 'رژ لب مایع با ماندگاری ۱۲ ساعته، بافت مخملی و رنگ‌دهی فوق‌العاده. فاقد پارابن و مناسب انواع پوست.',
  },
  {
    id: 2, name: 'کرم پودر فول‌کاور فاما SPF15', cat: 'face',
    price: 620000, oldPrice: null, rating: 4.6, reviews: 89,
    badge: 'hot', art: 'foundation', hue: ['#F9A8D4', '#DB2777'],
    desc: 'پوشش کامل و طبیعی با محافظت در برابر آفتاب. مناسب پوست‌های مختلط و ماندگاری بالا در طول روز.',
  },
  {
    id: 3, name: 'ریمل حجم‌دهنده و بلندکننده فاما', cat: 'eyes',
    price: 390000, oldPrice: 450000, rating: 4.7, reviews: 210,
    badge: 'sale', art: 'mascara', hue: ['#C4B5FD', '#7C3AED'],
    desc: 'برس سیلیکونی مخصوص برای حجم و بلندی مژه‌ها بدون کلوخه شدن. ضدآب و مقاوم در برابر رطوبت.',
  },
  {
    id: 4, name: 'پالت سایه چشم ۱۲ رنگ رزگلد', cat: 'eyes',
    price: 750000, oldPrice: null, rating: 4.9, reviews: 156,
    badge: 'new', art: 'palette', hue: ['#FBCFE8', '#EC4899'],
    desc: '۱۲ رنگ ترکیبی مات و شاین با پیگمنت بالا. مناسب میکاپ روزانه و مجلسی.',
  },
  {
    id: 5, name: 'سرم ویتامین C روشن‌کننده فاما', cat: 'skincare',
    price: 890000, oldPrice: 1050000, rating: 4.8, reviews: 302,
    badge: 'sale', art: 'serum', hue: ['#FDBA74', '#EA580C'],
    desc: 'سرم روشن‌کننده با ۱۵٪ ویتامین C خالص برای شفافیت و یکدست شدن رنگ پوست. مناسب استفاده روزانه.',
  },
  {
    id: 6, name: 'کرم آبرسان هیالورونیک اسید', cat: 'skincare',
    price: 540000, oldPrice: null, rating: 4.7, reviews: 178,
    badge: null, art: 'cream', hue: ['#93C5FD', '#2563EB'],
    desc: 'آبرسانی عمیق ۷۲ ساعته با هیالورونیک اسید و نیاسینامید. بدون چربی و مناسب همه انواع پوست.',
  },
  {
    id: 7, name: 'ادوپرفیوم زنانه FAMA Blossom', cat: 'fragrance',
    price: 1250000, oldPrice: null, rating: 4.9, reviews: 96,
    badge: 'new', art: 'perfume', hue: ['#F9A8D4', '#9D174D'],
    desc: 'رایحه گلی-میوه‌ای با نت‌های آغازین گل صدتومانی، رز و مشک سفید. ماندگاری بالا برای تمام روز.',
  },
  {
    id: 8, name: 'خط چشم ماژیکی ضدآب فاما', cat: 'eyes',
    price: 320000, oldPrice: 380000, rating: 4.5, reviews: 143,
    badge: 'sale', art: 'liner', hue: ['#A5B4FC', '#4338CA'],
    desc: 'نوک نمدی دقیق برای کشیدن خطی یکدست و مشکی عمیق. ضدآب و مقاوم تا ۲۴ ساعت.',
  },
  {
    id: 9, name: 'هایلایتر شاین طلایی-صورتی', cat: 'face',
    price: 460000, oldPrice: null, rating: 4.6, reviews: 67,
    badge: null, art: 'highlighter', hue: ['#FDE68A', '#D97706'],
    desc: 'درخشش طبیعی و ابریشمی برای گونه‌ها و نقاط برجسته صورت. قابل استفاده خشک و مرطوب.',
  },
  {
    id: 10, name: 'ماسک ورقه‌ای آبرسان گل رز', cat: 'skincare',
    price: 280000, oldPrice: null, rating: 4.4, reviews: 88,
    badge: null, art: 'mask', hue: ['#F9A8D4', '#DB2777'],
    desc: 'ماسک ورقه‌ای غنی‌شده با عصاره گل رز و آلوئه‌ورا برای آبرسانی و شادابی فوری پوست.',
  },
  {
    id: 11, name: 'لاک ناخن ژلی فاما — صورتی نئون', cat: 'tools',
    price: 150000, oldPrice: 185000, rating: 4.3, reviews: 54,
    badge: 'sale', art: 'polish', hue: ['#F472B6', '#BE185D'],
    desc: 'لاک ژلی براق با ماندگاری بالا و خشک شدن سریع، بدون نیاز به دستگاه UV.',
  },
  {
    id: 12, name: 'ست ۸ عددی براش آرایشی حرفه‌ای', cat: 'tools',
    price: 680000, oldPrice: null, rating: 4.8, reviews: 112,
    badge: 'hot', art: 'brush', hue: ['#C4B5FD', '#7C3AED'],
    desc: 'ست کامل براش صورت و چشم با موی مصنوعی نرم و دسته چوبی، همراه با کیف نگهداری.',
  },
];
