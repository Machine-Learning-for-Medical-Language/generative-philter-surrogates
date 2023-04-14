https://download.cms.gov/nppes/NPI_Files.html
https://data.cms.gov/provider-data/dataset/dgck-syfz


Goal is to be useful for training NLP models that can then be shared.

* Be realistic
  * To not accidentally train the model on odd data
* Be varied
  * To not accidentally train the model to always look for `Mike` for example  
* Do not change length
  - Mostly to not break any references to the note that other code might have


# Problems
- Too short, too long
- Overlapping ranges