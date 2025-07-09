"""
📰 NEWS PARSER
Парсер юридических новостей с различных сайтов
"""

import asyncio
import aiohttp
import re
import time
from datetime import datetime
from typing import List, Dict
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from .models import NewsItem

class NewsParser:
    """Интеллектуальный парсер юридических новостей"""
    
    def __init__(self):
        self.session = None
        self.sources = {
            'consultant': {
                'url': 'https://www.consultant.ru/legalnews/',
                'rss': 'https://www.consultant.ru/rss/legalnews.xml',
                'parser': self._parse_consultant
            },
            'pravo_gov': {
                'url': 'http://pravo.gov.ru/',
                'parser': self._parse_pravo_gov
            },
            'garant': {
                'url': 'https://www.garant.ru/news/',
                'parser': self._parse_garant
            }
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        self.request_delays = {'consultant': 2, 'pravo_gov': 3, 'garant': 2}
        self.last_requests = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def parse_all_sources(self) -> List[NewsItem]:
        """Парсинг всех источников"""
        all_news = []
        
        for source_name, source_config in self.sources.items():
            try:
                await self._respect_rate_limit(source_name)
                news_items = await source_config['parser'](source_config)
                all_news.extend(news_items)
            except Exception as e:
                print(f"❌ Failed to parse {source_name}: {e}")
                continue
        
        return all_news

    async def _respect_rate_limit(self, source: str):
        """Rate limiting"""
        delay = self.request_delays.get(source, 2)
        last_request = self.last_requests.get(source, 0)
        
        time_since_last = time.time() - last_request
        if time_since_last < delay:
            await asyncio.sleep(delay - time_since_last)
        
        self.last_requests[source] = time.time()

    async def _parse_consultant(self, config: Dict) -> List[NewsItem]:
        """Парсинг Consultant.ru"""
        items = []
        
        try:
            # RSS парсинг
            if 'rss' in config:
                items.extend(await self._parse_rss(config['rss'], 'consultant'))
            
            # HTML парсинг главной страницы
            async with self.session.get(config['url']) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    news_blocks = soup.find_all('div', class_=['news-item', 'news-block'])
                    
                    for block in news_blocks[:5]:
                        try:
                            title_elem = block.find(['h2', 'h3', 'a'])
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            
                            link_elem = block.find('a')
                            url = urljoin(config['url'], link_elem['href']) if link_elem else config['url']
                            
                            date_elem = block.find(['time', 'span'], class_=['date'])
                            publish_date = self._parse_date(date_elem.get_text() if date_elem else "")
                            
                            content_elem = block.find(['p', 'div'], class_=['annotation', 'desc'])
                            content = content_elem.get_text(strip=True) if content_elem else title
                            
                            category = self._extract_category(url, title, content)
                            
                            items.append(NewsItem(
                                title=title,
                                content=content,
                                url=url,
                                source='consultant',
                                publish_date=publish_date,
                                category=category
                            ))
                            
                        except Exception:
                            continue
        
        except Exception as e:
            print(f"Failed to parse consultant: {e}")
        
        return items

    async def _parse_pravo_gov(self, config: Dict) -> List[NewsItem]:
        """Парсинг Pravo.gov.ru"""
        items = []
        
        try:
            # Парсим новые НПА
            npa_url = "http://pravo.gov.ru/proxy/ips/?start_search&fattrib=1"
            
            async with self.session.get(npa_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    doc_links = soup.find_all('a', href=re.compile(r'/proxy/ips/\?doc'))
                    
                    for link in doc_links[:3]:
                        try:
                            title = link.get_text(strip=True)
                            url = urljoin("http://pravo.gov.ru", link['href'])
                            
                            items.append(NewsItem(
                                title=title,
                                content=f"Новый нормативный акт: {title}",
                                url=url,
                                source='pravo_gov',
                                publish_date=datetime.now(),
                                category='Нормативные акты'
                            ))
                            
                        except Exception:
                            continue
                            
        except Exception as e:
            print(f"Failed to parse pravo.gov.ru: {e}")
        
        return items

    async def _parse_garant(self, config: Dict) -> List[NewsItem]:
        """Парсинг Garant.ru"""
        items = []
        
        try:
            async with self.session.get(config['url']) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    news_items = soup.find_all(['div', 'article'], class_=['news'])
                    
                    for item in news_items[:3]:
                        try:
                            title_elem = item.find(['h3', 'h4', 'a'])
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            
                            link = item.find('a')
                            url = urljoin(config['url'], link['href']) if link else config['url']
                            
                            items.append(NewsItem(
                                title=title,
                                content=f"Правовая новость: {title}",
                                url=url,
                                source='garant',
                                publish_date=datetime.now(),
                                category='Правовые новости'
                            ))
                            
                        except Exception:
                            continue
                            
        except Exception as e:
            print(f"Failed to parse garant: {e}")
        
        return items

    async def _parse_rss(self, rss_url: str, source: str) -> List[NewsItem]:
        """RSS парсер"""
        items = []
        
        try:
            async with self.session.get(rss_url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    root = ET.fromstring(xml_content)
                    
                    for item in root.findall('.//item')[:5]:
                        try:
                            title = item.find('title')
                            title_text = title.text if title is not None else "Без заголовка"
                            
                            description = item.find('description')
                            content = description.text if description is not None else title_text
                            
                            link = item.find('link')
                            url = link.text if link is not None else rss_url
                            
                            pub_date = item.find('pubDate')
                            publish_date = self._parse_date(pub_date.text if pub_date is not None else "")
                            
                            category = self._extract_category(url, title_text, content)
                            
                            items.append(NewsItem(
                                title=title_text,
                                content=content,
                                url=url,
                                source=source,
                                publish_date=publish_date,
                                category=category
                            ))
                            
                        except Exception:
                            continue
                            
        except Exception as e:
            print(f"Failed to parse RSS {rss_url}: {e}")
        
        return items

    def _parse_date(self, date_str: str) -> datetime:
        """Парсинг даты"""
        if not date_str:
            return datetime.now()
        
        date_patterns = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y %H:%M',
            '%d.%m.%Y',
            '%Y-%m-%d'
        ]
        
        for pattern in date_patterns:
            try:
                return datetime.strptime(date_str.strip(), pattern)
            except ValueError:
                continue
        
        return datetime.now()

    def _extract_category(self, url: str, title: str, content: str) -> str:
        """Категоризация"""
        text = f"{title} {content}".lower()
        
        categories = {
            'Семейное право': ['семейн', 'развод', 'алимент', 'брак'],
            'Трудовое право': ['труд', 'работ', 'увольнен', 'зарплат'],
            'Налоговое право': ['налог', 'ндфл', 'ифнс'],
            'Административное право': ['админ', 'штраф', 'коап'],
            'Нормативные акты': ['федеральн', 'закон', 'постановлен']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'Общее право'
