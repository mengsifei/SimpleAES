import torch
import numpy as np

class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, df, tokenizer, max_len=512):
        self.tokenizer = tokenizer
        self.df = df
        self.text = df['essay']
        self.topic = df['prompt']
        self.labels = df[['Task Response', 'Coherence and Cohesion',
                          'Lexical Resource', 'Grammatical Range and Accuracy']].values
        self.max_len = max_len
        self.weights = self.calculate_weights(df, dampening_factor=0.8)

    def __len__(self):
        return len(self.text)

    def calculate_weights(df, dampening_factor=0.8):
        rubrics = ['Task Response', 'Coherence and Cohesion', 'Lexical Resource', 'Grammatical Range and Accuracy']
        weights = {}
        for criterion in rubrics:
            value_counts = df[criterion].value_counts().sort_index()
            total_counts = sum(value_counts)
            weights[criterion] = total_counts / value_counts  # Inverse of frequency
            weights[criterion] = (weights[criterion] ** dampening_factor)  # Dampen the effect
            weights[criterion] /= weights[criterion].mean()   # Normalize
        return weights

    def __getitem__(self, index):
        text = self.text[index]
        topic = self.topic[index]
        combined_text = f"[TOPIC] {topic} [TOPIC] {topic} [ESSAY] {text}"
        inputs = self.tokenizer.encode_plus(    
            combined_text,
            None,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            return_token_type_ids=True,
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        label_weights = np.array([
            self.weights['Task Response'][self.labels[index, 0]],
            self.weights['Coherence and Cohesion'][self.labels[index, 1]],
            self.weights['Lexical Resource'][self.labels[index, 2]],
            self.weights['Grammatical Range and Accuracy'][self.labels[index, 3]]
        ])
        return {
            'input_ids': inputs['input_ids'].flatten(),
            'attention_mask': inputs['attention_mask'].flatten(),
            'token_type_ids': inputs['token_type_ids'].flatten(),
            'labels': torch.FloatTensor(self.labels[index]),
            'label_weights': torch.FloatTensor(label_weights)
        }
    

class CustomDatasetSegment(torch.utils.data.Dataset):
    def __init__(self, df, tokenizer, max_len=512):
        self.tokenizer = tokenizer
        self.df = df
        self.text = df['essay']
        self.topic = df['prompt']
        self.labels = self.df[['Task Response', 'Coherence and Cohesion',
       'Lexical Resource', 'Grammatical Range and Accuracy']].values
        self.max_len = max_len

    def __len__(self):
        return len(self.text)

    def __getitem__(self, index):
        text = self.text[index]
        topic = self.topic[index]
        inputs = self.tokenizer.encode_plus(
            [topic.replace('\n', ''), text.replace("\n", f" [SEP][SEP] ")],
            None,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            return_token_type_ids=True,
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        return {
            'input_ids': inputs['input_ids'].flatten(),
            'attention_mask': inputs['attention_mask'].flatten(),
            'token_type_ids': inputs['token_type_ids'].flatten(),
            'labels': torch.FloatTensor(list(self.labels[index]))
        }


class CustomDatasetDual(torch.utils.data.Dataset):
    def __init__(self, df, tokenizer, max_len=512):
        self.tokenizer = tokenizer
        self.df = df
        self.essays = df['essay']
        self.topics = df['prompt']
        self.labels = df[['Task Response', 'Coherence and Cohesion', 'Lexical Resource', 'Grammatical Range and Accuracy']].values
        self.max_len = max_len

    def __len__(self):
        return len(self.essays)

    def __getitem__(self, index):
        essay_text = self.essays[index]
        topic_text = self.topics[index]
        essay_text = essay_text.replace("\n", f" [SEP] ")
        essay_inputs = self.tokenizer(
            essay_text,
            max_length=self.max_len - 60, 
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        topic_inputs = self.tokenizer(
            topic_text,
            max_length=60,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'essay_input_ids': essay_inputs['input_ids'].flatten(),
            'essay_attention_mask': essay_inputs['attention_mask'].flatten(),
            'topic_input_ids': topic_inputs['input_ids'].flatten(),
            'topic_attention_mask': topic_inputs['attention_mask'].flatten(),
            'labels': torch.FloatTensor(self.labels[index])
        }
    
