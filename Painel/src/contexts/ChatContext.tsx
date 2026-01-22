import React, { createContext, useContext, useState, ReactNode } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatContextType {
  messages: Message[];
  isOpen: boolean;
  isLoading: boolean;
  toggleChat: () => void;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

const generateAIResponse = async (userMessage: string, messages: Message[]): Promise<string> => {
  // Simulated AI responses based on context
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  const lowerMessage = userMessage.toLowerCase();
  
  if (lowerMessage.includes('faturamento') || lowerMessage.includes('receita')) {
    return 'Analisando seus dados de faturamento... O faturamento total atual é de R$ 847.500,00. Houve um crescimento de 12,5% em comparação ao período anterior. A inadimplência está em R$ 23.400,00 (2,8%), dentro do limite saudável. Posso gerar um plano de ação para melhorar esses números?';
  }
  
  if (lowerMessage.includes('plano') || lowerMessage.includes('ação') || lowerMessage.includes('melhorar')) {
    return `📋 **Plano de Ação Recomendado:**

1. **Redução de Inadimplência**
   - Implementar lembretes automáticos 3 dias antes do vencimento
   - Oferecer desconto de 5% para pagamento antecipado

2. **Aumento de Faturamento**
   - Identificar clientes com potencial de upsell
   - Lançar campanha de indicação com benefícios

3. **Otimização de Custos**
   - Revisar contratos com fornecedores
   - Automatizar processos manuais

Quer que eu detalhe algum desses pontos?`;
  }
  
  if (lowerMessage.includes('cliente')) {
    return 'Você tem 156 clientes ativos no momento. Desses, 23 são clientes premium com faturamento acima de R$ 10.000/mês. Posso ajudar a identificar oportunidades de crescimento com clientes específicos?';
  }
  
  if (lowerMessage.includes('olá') || lowerMessage.includes('oi') || lowerMessage.includes('bom dia') || lowerMessage.includes('boa tarde')) {
    return 'Olá! 👋 Sou seu assistente de gestão. Posso ajudar com:\n\n• Análise de faturamento e métricas\n• Geração de planos de ação\n• Informações sobre clientes\n• Insights e recomendações\n\nComo posso ajudar hoje?';
  }
  
  return 'Entendi sua mensagem. Posso ajudar com análises de faturamento, dados de clientes ou gerar planos de ação personalizados. O que você gostaria de saber?';
};

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Olá! 👋 Sou seu assistente de gestão. Como posso ajudar hoje?',
      timestamp: new Date(),
    },
  ]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const toggleChat = () => setIsOpen(prev => !prev);

  const sendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await generateAIResponse(content, messages);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error generating response:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const clearMessages = () => {
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: 'Olá! 👋 Sou seu assistente de gestão. Como posso ajudar hoje?',
        timestamp: new Date(),
      },
    ]);
  };

  return (
    <ChatContext.Provider value={{ messages, isOpen, isLoading, toggleChat, sendMessage, clearMessages }}>
      {children}
    </ChatContext.Provider>
  );
};
