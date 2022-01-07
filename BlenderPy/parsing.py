# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 20:55:45 2021

@author: Thibault
"""

class Node:
    
    def __init__(self, name='X'):
        self.name

class Token:
    
    def __init__(self, token_type='', content=''):
        self.token_type=token_type
        self.content=content

class Operator:
    
    def __init__(self, left=None, right=None):
        self.left=left
        self.right=right

class Expression:
    
    specials=['(',')','+','-','/','*','^','e','|', '>', '<', 's', 'c']
    numbers=['.','0','1','2','3','4','5','6','7','8','9']
    nodes=['x','y','z', 'X', 'Y', 'Z']
    
    def __init__(self, content='', nodes=[], operation=None, tokens=[]):
        self.shader=None
        self.content=content
        self.nodes=nodes
        self.operation=operation
        self.tokens=tokens
        self.lexer()
        self.absolute()
        self.parenthesis()
        self.parse()
        self.clean_tree()
    
    def lexer(self):
        i=0
        previous_token=None
        while i<len(self.content):
            
            if self.content[i] in Expression.specials:
                if self.content[i] in ['e', '(', '|'] and previous_token is None:
                    token=Token('operator',self.content[i])
                    self.tokens.append(token)
                    previous_token=token
                elif self.content[i]=='-' and previous_token is None:
                    token=Token('number','-1')
                    self.tokens.append(token)
                    token=Token('operator','*')
                    self.tokens.append(token)
                    previous_token=token
                elif self.content[i]=='-' and previous_token.content in ['(','^','+','/','*','|','<','>']:
                    token=Token('number','-1')
                    self.tokens.append(token)
                    token=Token('operator','*')
                    self.tokens.append(token)
                    previous_token=token
                elif self.content[i] in ['(','e'] and \
                previous_token.content in Expression.numbers:
                    token=Token('operator','*')
                    self.tokens.append(token)
                    token=Token('operator',self.content[i])
                    self.tokens.append(token)
                    previous_token=token
                elif self.content[i] =='s':
                    if i+3<len(self.content):
                        if self.content[i:i+4]=='sqrt':
                            token=Token('operator','sqrt')
                            self.tokens.append(token)
                            previous_token=token
                            i+=3
                    if i+2<len(self.content):
                        if self.content[i:i+3]=='sin':
                            token=Token('operator','sin')
                            self.tokens.append(token)
                            previous_token=token
                            i+=2
                elif self.content[i] =='c':
                    if i+3<len(self.content):
                        if self.content[i:i+3]=='cos':
                            token=Token('operator','cos')
                            self.tokens.append(token)
                            previous_token=token
                            i+=2
                else:
                    token=Token('operator',self.content[i])
                    previous_token=token
                    self.tokens.append(token)
                i+=1
            elif self.content[i] in Expression.numbers:
                if previous_token is not None and previous_token.content in Expression.numbers:
                    token=Token('operator','*')
                    self.tokens.append(token)
                j=0
                end=False
                while not(end):
                    if i+j<len(self.content):
                        if self.content[i+j] in Expression.numbers:
                            j+=1
                        else:
                            end=True
                    else:
                        end=True
                token=Token('number',self.content[i:i+j])
                self.tokens.append(token)
                previous_token=token
                i=i+j
            elif self.content[i] in Expression.nodes:
                if previous_token is not None and previous_token.content in Expression.numbers:
                    token=Token('operator','*')
                    self.tokens.append(token)
                token=Token('number',self.content[i])
                self.tokens.append(token)
                previous_token=token
                i+=1
            else:
                print("unexpected character")
    
    def parenthesis(self):
        done=False
        while not done:
            ind_start, ind_stop=None, None
            for i,t in enumerate(self.tokens):
                if t.content=='(':
                     ind_start=i
                elif t.content==')':
                     ind_stop=i
                     break
            if ind_start is not None and ind_stop is not None:
                tokens=self.tokens[ind_start+1:ind_stop]
                for i in range(ind_start, ind_stop+1)[::-1]:
                    self.tokens.pop(i)
                node=Expression(tokens=tokens)
                self.tokens.insert(ind_start,node)
            else:
                done=True
    
    def absolute(self):
        ind_start, ind_stop=None, None
        for i,t in enumerate(self.tokens):
            if t.content=='|':
                if ind_start is None:
                    ind_start=i
                else:
                    ind_stop=i
                    tokens=self.tokens[ind_start+1:ind_stop]
                    for i in range(ind_start, ind_stop+1)[::-1]:
                        self.tokens.pop(i)
                    
                    node=Expression(tokens=tokens, operation='ABS')
                    self.tokens.insert(ind_start,node)
                    ind_start, ind_stop=None, None 
    
    def parse(self):
        operation_found=False
        if self.operation is not None:
            self.nodes=[Expression(tokens=self.tokens)]
        else:
            for i,t in enumerate(self.tokens):
                if t.content in ['+','-']:
                    operation_found=True
                    node_1=Expression(tokens=self.tokens[:i])
                    node_2=Expression(tokens=self.tokens[i+1:])
                    self.nodes=[node_1, node_2]
                    self.operation=t.content
            if not operation_found:
                for i,t in enumerate(self.tokens):
                    if t.content in ['*','/', '>', '<']:
                        operation_found=True
                        node_1=Expression(tokens=self.tokens[:i])
                        node_2=Expression(tokens=self.tokens[i+1:])
                        self.nodes=[node_1, node_2]
                        self.operation=t.content
            if not operation_found:
                for i,t in enumerate(self.tokens):
                    if t.content in ['^']:
                        operation_found=True
                        node_1=Expression(tokens=self.tokens[:i])
                        node_2=Expression(tokens=self.tokens[i+1:])
                        self.nodes=[node_1, node_2]
                        self.operation=t.content
                    elif t.content in ['sqrt', 'sin', 'cos']:
                        operation_found=True
                        node_1=Expression(tokens=self.tokens[i+1:])
                        self.nodes=[node_1]
                        self.operation=t.content
    
    
    def is_leaf(self):
        return len(self.tokens)==1 and not isinstance(self.tokens[0], Expression) and self.operation is None
                    
    def get_leaves(self):
        if self.is_leaf():
            return [self.tokens[0].content]
        leaves=[]
        if len(self.tokens)==1 and isinstance(self.tokens[0], Expression):
            leaves+=self.tokens[0].get_leaves()
        else:
            for node in self.nodes:
                leaves+=node.get_leaves()
        return leaves
    
    def clean_tree(self):
        for i, node in enumerate(self.nodes):
            if len(node.tokens)==1 and isinstance(node.tokens[0], Expression):
                self.nodes[i]=node.tokens[0]
        if len(self.tokens)==1 and len(self.nodes)==0 and self.operation is None and isinstance(self.tokens[0], Expression):
            self.__dict__.update(self.tokens[0].__dict__)
    
    def get_tree(self):
        if self.is_leaf():
            return self.tokens[0].content
        else:
            return dict({self.operation:[node.get_tree() for node in self.nodes]})
        
        

if __name__=='__main__':
    expression=Expression(content='cos(|x-0.5|*3.14/0.1)', tokens=[])
    res=expression.get_tree()
    
            
    