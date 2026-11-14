# Eval review: what Unclaimed is tested on

All programs are fictional and live in `evals/corpus/` (2 pages each: page 1 = benefit and who can apply, page 2 = documents and exclusions).

## Programs

| Program | File |
|---|---|
| Child Nutrition Grant | `child-nutrition-grant.txt` |
| Disability Allowance | `disability-allowance.txt` |
| Family Health Cover | `family-health-cover.txt` |
| Farm Income Support | `farm-income-support.txt` |
| Gig Worker Accident Cover | `gig-worker-accident-cover.txt` |
| Higher Education Scholarship | `higher-education-scholarship.txt` |
| Maternity Support Payment | `maternity-support-payment.txt` |
| Rural Housing Grant | `rural-housing-grant.txt` |
| Senior Citizen Pension | `senior-citizen-pension.txt` |
| Skills Training Stipend | `skills-training-stipend.txt` |
| Startup Business Loan | `startup-business-loan.txt` |
| Street Vendor Working Capital Loan | `street-vendor-loan.txt` |

## Test people

**Must find** = the answer must list these. **Must NOT list** = listing these is a wrong answer. Programs in neither column are neither rewarded nor penalised.

| id | type | person | must find | must NOT list |
|---|---|---|---|---|
| c01 | single | I'm a 35-year-old farmer and I own 3 acres where I grow wheat. | Farm Income Support | — |
| c02 | single | I deliver food on a bike for an app. I'm 27. | Gig Worker Accident Cover | — |
| c03 | single | I'm 24 and 4 months pregnant with my first child. | Maternity Support Payment | — |
| c04 | multi | My mother is 72. Our whole household earns about 60000 a year. | Senior Citizen Pension, Family Health Cover | — |
| c05 | single | I just got into university. I scored 78% in my final school exams and my parents earn 180000 a year. | Higher Education Scholarship | Family Health Cover |
| c06 | single | I sell vegetables from a cart on the roadside. I have a vending certificate and need money for stock. | Street Vendor Working Capital Loan | — |
| c07 | single | I'm 30 and want to open a small tailoring shop. I've never run a business before. | Startup Business Loan | — |
| c08 | single | I'm 26. I lost my left leg in an accident and my medical board certificate says 60% disability. | Disability Allowance | — |
| c09 | single | We live in a village in a mud house with a thatched roof, on land we own. | Rural Housing Grant | — |
| c10 | multi | 24 year old rideshare driver, married, one kid aged 3. | Gig Worker Accident Cover, Child Nutrition Grant | — |
| c11 | multi | I'm a 30-year-old farmer with 2 acres of my own land. My wife just gave birth to our second baby. | Farm Income Support, Maternity Support Payment, Child Nutrition Grant | — |
| c12 | multi | I'm 22, unemployed, finished 10 years of school, and our family earns 90000 a year. | Skills Training Stipend, Family Health Cover | — |
| c13 | near-miss | I own 12 acres of farmland. Can I get farm income support? | — | Farm Income Support |
| c14 | near-miss | I'm 58. Can I get the old age pension yet? | — | Senior Citizen Pension |
| c15 | near-miss | I'm 50 and want to start my first business, a small bakery. | — | Startup Business Loan |
| c16 | near-miss | I have a certified disability of 25% from a work injury. | — | Disability Allowance |
| c17 | near-miss | My son is 8 years old. Can I get the child nutrition grant? | — | Child Nutrition Grant |
| c18 | near-miss | I'm in college but scored 52% in my last exam. My family earns 100000 a year. | Family Health Cover | Higher Education Scholarship |
| c19 | near-miss | I'm 28 and pregnant with my third child. | — | Maternity Support Payment |
| c20 | no-match | What's the best pizza topping? | **nothing at all** | — |
| c21 | no-match | I'm a software engineer earning 2500000 a year, single, no kids, living in the city. | **nothing at all** | — |
| c22 | no-match | How do I renew my driving license? | **nothing at all** | — |
| c23 | vague | I'm a farmer. | — (must ask for missing info) | — |
| c24 | vague | I'm a 65-year-old widow. | — (must ask for missing info) | — |
| c25 | follow-up | *(follow-up to: 24 year old rideshare driver, married, one kid aged 3.)* What about my wife? She's 23 and pregnant with our second child. | Maternity Support Payment | — |
