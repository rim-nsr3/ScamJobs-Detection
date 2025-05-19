from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os

# Cities with large tech job markets
CITIES = [
    'chicago', 'newyork', 'losangeles', 'sfbay', 'seattle', 
    'austin', 'boston', 'miami', 'atlanta', 'dallas'
]

#  job categories
CATEGORIES = {
    'sof': 'software/web/info design',
    'tch': 'computer/technical support',
    'sad': 'systems/networking',
    'web': 'web/html/info design',
    'cpg': 'computer/engineering/cad',
    'eng': 'engineering',
    'sci': 'science/biotech',
    'eng': 'internet engineering'
}

# Total number of posts to collect
TARGET_POSTS = 500

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    # user agent to avoid detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        exit(1)

def get_job_links(driver, city, category):
    url = f"https://{city}.craigslist.org/search/{category}"
    print(f"Navigating to {url}")
    driver.get(url)
    
    # sleep to avoid detection (between 3-7 seconds)
    time.sleep(random.uniform(3, 7))
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    print(f"Page title: {soup.title.text}")
    
    # from the logs
    posts = soup.select('div.result-info')
    print(f"Found {len(posts)} job posts.")
    
    links = []
    for post in posts:
        a_tag = post.find('a', href=True)
        if a_tag:
            links.append(a_tag['href'])
    
    # make sure all links are URLs
    for i in range(len(links)):
        if not links[i].startswith('http'):
            links[i] = f"https://{city}.craigslist.org{links[i]}"
    
    # to get a more diverse sample
    random.shuffle(links)
    
    return links

def scrape_job(driver, url, city, category):
    try:
        print(f"Scraping job at {url}")
        driver.get(url)
        
        time.sleep(random.uniform(2, 5))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Get job title
        title_tag = soup.find('span', id='titletextonly')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Get job description
        description_tag = soup.find('section', id='postingbody')
        description = ''
        if description_tag:
            description = description_tag.get_text(strip=True)
            if "QR Code Link to This Post" in description:
                description = description.replace("QR Code Link to This Post", "").strip()
        
        # Get compensation if available
        compensation = ''
        comp_tag = soup.select_one('.attrgroup .remuneration .valu')
        if comp_tag:
            compensation = comp_tag.get_text(strip=True)
        
        # Get employment type if available
        employment_type = ''
        emp_type_tag = soup.select_one('.attrgroup .employment_type .valu')
        if emp_type_tag:
            employment_type = emp_type_tag.get_text(strip=True)
        
        # Get job location/area
        location = ''
        location_tag = soup.select_one('.postingtitletext > span:last-child')
        if location_tag:
            location = location_tag.get_text(strip=True).strip('()')
        
        # Get company name if available
        company = ''
        company_tag = soup.select_one('h2.company-name')
        if company_tag:
            company = company_tag.get_text(strip=True)
        
        # Get post date
        post_date = ''
        date_tag = soup.select_one('p.postinginfo time')
        if date_tag and date_tag.has_attr('datetime'):
            post_date = date_tag['datetime']
        
        return {
            'url': url,
            'title': title,
            'description': description,
            'compensation': compensation,
            'employment_type': employment_type,
            'location': location,
            'company': company,
            'post_date': post_date,
            'city': city,
            'category': CATEGORIES.get(category, category),
            'is_scam': ''  # to fill in  (1 for scam, 0 for legitimate)
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    print("Starting Tech Job Scraper...")
    driver = setup_driver()
    all_jobs = []
    
    # Load existing jobs if available to avoid re-scraping
    if os.path.exists("tech_jobs_raw.csv"):
        existing_df = pd.read_csv("tech_jobs_raw.csv")
        all_jobs = existing_df.to_dict('records')
        print(f"Loaded {len(all_jobs)} existing job records.")
    
    # Calculate how many more jobs we need
    remaining_jobs = max(0, TARGET_POSTS - len(all_jobs))
    
    if remaining_jobs > 0:
        print(f"Need to scrape {remaining_jobs} more jobs...")
        
        # Distribute jobs evenly across cities and categories
        posts_per_city_category = max(1, remaining_jobs // (len(CITIES) * len(CATEGORIES)))
        print(f"Planning to scrape approximately {posts_per_city_category} jobs per city/category")
        
        # Keep track of unique URLs to avoid duplicates
        existing_urls = set(job['url'] for job in all_jobs if 'url' in job)
        
        # Randomize order of cities and categories to get better distribution
        random_cities = CITIES.copy()
        random.shuffle(random_cities)
        
        for city in random_cities:
            if len(all_jobs) >= TARGET_POSTS:
                break
                
            random_categories = list(CATEGORIES.keys())
            random.shuffle(random_categories)
            
            for category in random_categories:
                if len(all_jobs) >= TARGET_POSTS:
                    break
                    
                print(f"\nScraping {city} - {CATEGORIES[category]}...")
                links = get_job_links(driver, city, category)
                print(f"Found {len(links)} links.")
                
                # Filter out already scraped URLs
                new_links = [link for link in links if link not in existing_urls]
                print(f"{len(new_links)} new links to process.")
                
                if not new_links:
                    print(f"No new links found for {city}/{category}. Skipping.")
                    continue
                
                # Limit number of jobs to scrape for this city/category
                links_to_scrape = new_links[:posts_per_city_category]
                
                for i, link in enumerate(links_to_scrape):
                    if len(all_jobs) >= TARGET_POSTS:
                        break
                        
                    print(f"Processing job {i+1}/{len(links_to_scrape)} ({len(all_jobs)+1}/{TARGET_POSTS})")
                    job = scrape_job(driver, link, city, category)
                    
                    if job:
                        all_jobs.append(job)
                        existing_urls.add(link)
                        
                        # Save progress after every 25 jobs
                        if len(all_jobs) % 25 == 0:
                            temp_df = pd.DataFrame(all_jobs)
                            temp_df.to_csv("tech_jobs_raw_progress.csv", index=False)
                            print(f"Progress saved: {len(all_jobs)} jobs so far ({len(all_jobs)/TARGET_POSTS*100:.1f}%)")
    
    driver.quit()
    
    if all_jobs:
        output_file = "tech_jobs_raw.csv"
        df = pd.DataFrame(all_jobs)
        df.to_csv(output_file, index=False)
        print(f"\n✅ Saved {output_file} with {len(all_jobs)} jobs")
        
        print("\nJobs by city:")
        city_counts = df['city'].value_counts()
        for city, count in city_counts.items():
            print(f"  {city}: {count} jobs ({count/len(df)*100:.1f}%)")
        
        print("\nJobs by category:")
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            print(f"  {category}: {count} jobs ({count/len(df)*100:.1f}%)")
    else:
        print("\n No jobs were scraped.")

if __name__ == "__main__":
    main()